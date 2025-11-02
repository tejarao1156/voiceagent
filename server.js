const { createServer } = require('http');
const { parse } = require('url');
const next = require('next');
const WebSocket = require('ws');

const dev = process.env.NODE_ENV !== 'production';
const hostname = 'localhost';
const port = 3000;

const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const server = createServer(async (req, res) => {
    try {
      const parsedUrl = parse(req.url, true);
      await handle(req, res, parsedUrl);
    } catch (err) {
      console.error('Error occurred handling', req.url, err);
      res.statusCode = 500;
      res.end('internal server error');
    }
  });

  // WebSocket proxy server
  const wss = new WebSocket.Server({ noServer: true });

  server.on('upgrade', async (request, socket, head) => {
    const { pathname, query } = parse(request.url, true);

    if (pathname === '/api/ws-proxy') {
      const sessionId = query.session_id;
      
      if (!sessionId) {
        socket.write('HTTP/1.1 400 Bad Request\r\n\r\n');
        socket.destroy();
        return;
      }

      // Connect to OpenAI Realtime API WebSocket
      // Session ID in query params is sufficient for authentication
      const openaiWsUrl = `wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17&session_id=${sessionId}`;
      const openaiWs = new WebSocket(openaiWsUrl);

      wss.handleUpgrade(request, socket, head, (ws) => {
        // Handle OpenAI WebSocket connection lifecycle
        openaiWs.on('open', () => {
          console.log('✅ Connected to OpenAI Realtime API');
        });

        openaiWs.on('error', (error) => {
          console.error('❌ OpenAI WebSocket error:', error.message);
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'error',
              error: { message: error.message }
            }));
          }
        });

        openaiWs.on('close', (code, reason) => {
          console.log('🔌 OpenAI WebSocket closed:', code, reason.toString());
          if (ws.readyState === WebSocket.OPEN) {
            ws.close();
          }
        });

        // Proxy messages from client to OpenAI
        ws.on('message', (data) => {
          try {
            if (openaiWs.readyState === WebSocket.OPEN) {
              openaiWs.send(data);
            } else {
              console.warn('⚠️ OpenAI WebSocket not open, dropping message');
            }
          } catch (error) {
            console.error('Error forwarding message to OpenAI:', error);
          }
        });

        // Proxy messages from OpenAI to client
        openaiWs.on('message', (data) => {
          try {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(data);
            }
          } catch (error) {
            console.error('Error forwarding message to client:', error);
          }
        });

        ws.on('error', (error) => {
          console.error('❌ Client WebSocket error:', error.message);
        });

        ws.on('close', () => {
          console.log('🔌 Client WebSocket closed');
          if (openaiWs.readyState === WebSocket.OPEN || openaiWs.readyState === WebSocket.CONNECTING) {
            openaiWs.close();
          }
        });
      });
    } else {
      socket.destroy();
    }
  });

  server.listen(port, (err) => {
    if (err) throw err;
    console.log(`> Ready on http://${hostname}:${port}`);
  });
});

