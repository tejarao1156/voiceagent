"""
Environment Detection Utility
Detects if the application is running locally or in a Kubernetes pod
"""
import os
import socket
import logging
import requests
from typing import Literal, Optional

logger = logging.getLogger(__name__)

def detect_runtime_environment() -> Literal["local", "kubernetes", "docker", "unknown"]:
    """
    Detect where the application is running.
    
    Returns:
        'local': Running on local machine (not containerized)
        'kubernetes': Running in Kubernetes pod
        'docker': Running in Docker container (but not Kubernetes)
        'unknown': Cannot determine
    """
    # Priority 1: Check explicit environment variable (highest priority)
    explicit_env = os.getenv("RUNTIME_ENVIRONMENT")
    if explicit_env in ["local", "kubernetes", "docker"]:
        logger.info(f"🔍 Environment explicitly set to: {explicit_env}")
        return explicit_env
    
    # Priority 2: Check Kubernetes-specific indicators
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        logger.info("🔍 Detected Kubernetes: KUBERNETES_SERVICE_HOST is set")
        return "kubernetes"
    
    # Check for Kubernetes service account token (mounted in pods)
    if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
        logger.info("🔍 Detected Kubernetes: Service account token found")
        return "kubernetes"
    
    # Check for Kubernetes namespace file
    if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/namespace"):
        logger.info("🔍 Detected Kubernetes: Namespace file found")
        return "kubernetes"
    
    # Priority 3: Check if running in container
    is_container = False
    
    # Check for .dockerenv file (Docker creates this)
    if os.path.exists("/.dockerenv"):
        is_container = True
        logger.debug("🔍 Found /.dockerenv - running in container")
    
    # Check cgroup for container indicators
    if os.path.exists("/proc/self/cgroup"):
        try:
            with open("/proc/self/cgroup", "r") as f:
                cgroup_content = f.read()
                if "docker" in cgroup_content or "kubepods" in cgroup_content:
                    is_container = True
                    logger.debug("🔍 Found container indicators in cgroup")
                    
                    # Check specifically for Kubernetes (kubepods)
                    if "kubepods" in cgroup_content:
                        logger.info("🔍 Detected Kubernetes: kubepods in cgroup")
                        return "kubernetes"
        except Exception as e:
            logger.debug(f"Could not read cgroup: {e}")
    
    if is_container:
        # We're in a container, but not Kubernetes
        logger.info("🔍 Detected Docker container (not Kubernetes)")
        return "docker"
    
    # Priority 4: Check hostname pattern (Kubernetes pods have specific naming)
    hostname = socket.gethostname()
    if hostname:
        # Kubernetes pod hostnames: deployment-name-random-string
        # e.g., "voice-agent-7d4f8b9c6-abc123"
        if "-" in hostname and len(hostname) > 15:
            parts = hostname.split("-")
            if len(parts) >= 3:
                # Check if last part looks like random string (hex, typical of pod names)
                try:
                    int(parts[-1], 16)  # Try to parse as hex
                    logger.info(f"🔍 Detected Kubernetes: Pod-like hostname pattern: {hostname}")
                    return "kubernetes"
                except ValueError:
                    pass
    
    # Priority 5: Check for pod-specific environment variables
    if os.getenv("POD_NAME") or os.getenv("POD_NAMESPACE"):
        logger.info("🔍 Detected Kubernetes: POD_NAME or POD_NAMESPACE set")
        return "kubernetes"
    
    # Default: assume local
    logger.info("🔍 Detected local environment (default)")
    return "local"


def get_ngrok_url_from_api() -> Optional[str]:
    """
    Automatically query ngrok API to get the public URL.
    
    ngrok exposes a local API at http://localhost:4040/api/tunnels
    that we can query to get the current public URL.
    
    Returns:
        ngrok public URL if ngrok is running, None otherwise
    """
    try:
        # ngrok API is at http://localhost:4040
        ngrok_api_url = os.getenv("NGROK_API_URL", "http://localhost:4040")
        tunnels_url = f"{ngrok_api_url}/api/tunnels"
        
        # Query ngrok API with short timeout (1 second) to avoid blocking
        response = requests.get(tunnels_url, timeout=1)
        
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get("tunnels", [])
            
            # Prefer HTTPS tunnel (required by Twilio)
            for tunnel in tunnels:
                public_url = tunnel.get("public_url", "")
                if public_url.startswith("https://"):
                    logger.info(f"🔗 Auto-detected ngrok URL from API: {public_url}")
                    return public_url.rstrip('/')
            
            # Fallback to HTTP tunnel if no HTTPS
            for tunnel in tunnels:
                public_url = tunnel.get("public_url", "")
                if public_url.startswith("http://"):
                    logger.warning(f"⚠️  Auto-detected ngrok HTTP URL (Twilio needs HTTPS): {public_url}")
                    return public_url.rstrip('/')
        
        return None
    except requests.exceptions.ConnectionError:
        # ngrok is not running
        return None
    except requests.exceptions.Timeout:
        # ngrok API not responding
        return None
    except Exception as e:
        logger.debug(f"Could not query ngrok API: {e}")
        return None


def get_webhook_base_url() -> str:
    """
    Get webhook base URL based on detected environment.
    
    Priority:
    1. Explicit TWILIO_WEBHOOK_BASE_URL environment variable
    2. Environment-specific defaults based on runtime detection
    """
    # Priority 1: Explicitly set (highest priority)
    explicit_url = os.getenv("TWILIO_WEBHOOK_BASE_URL")
    # Check if it's set and not the default localhost value
    if explicit_url and explicit_url.strip():
        # Don't use if it's the default localhost fallback
        # Check for common localhost patterns
        localhost_patterns = [
            "http://0.0.0.0",
            "http://localhost",
            "http://127.0.0.1",
            f"http://{os.getenv('API_HOST', '0.0.0.0')}:{os.getenv('API_PORT', '4002')}"
        ]
        is_localhost = any(explicit_url.startswith(pattern) for pattern in localhost_patterns)
        
        if not is_localhost:
            logger.info(f"🌐 Using explicit webhook URL: {explicit_url}")
            return explicit_url.rstrip('/')
        else:
            logger.debug(f"🌐 Explicit URL is localhost, skipping: {explicit_url}")
    
    # Priority 2: Environment-based auto-detection
    environment = detect_runtime_environment()
    
    if environment == "kubernetes":
        # Kubernetes: Use service URL or ingress
        ingress_url = os.getenv("INGRESS_URL")
        if ingress_url:
            logger.info(f"🌐 Using Kubernetes ingress URL: {ingress_url}")
            return ingress_url.rstrip('/')
        
        service_url = os.getenv("SERVICE_URL")
        if service_url:
            logger.info(f"🌐 Using Kubernetes service URL: {service_url}")
            return service_url.rstrip('/')
        
        # Fallback: Construct from service name and domain
        service_name = os.getenv("SERVICE_NAME", "voice-agent")
        namespace = os.getenv("POD_NAMESPACE", "default")
        domain = os.getenv("INGRESS_DOMAIN")
        
        if domain:
            constructed_url = f"https://api.{domain}"
            logger.info(f"🌐 Constructed Kubernetes URL from domain: {constructed_url}")
            return constructed_url
        
        # Last resort: Use service name (won't work externally, but good for internal)
        logger.warning("⚠️  No Kubernetes URL configured, using service name (may not work externally)")
        return f"https://{service_name}.{namespace}.svc.cluster.local"
    
    elif environment == "docker":
        # Docker: Could be local or cloud
        # Check if ngrok is available
        ngrok_url = os.getenv("NGROK_URL")
        if ngrok_url:
            logger.info(f"🌐 Using ngrok URL: {ngrok_url}")
            return ngrok_url.rstrip('/')
        
        # Check if there's a public URL set
        public_url = os.getenv("PUBLIC_URL")
        if public_url:
            logger.info(f"🌐 Using public URL: {public_url}")
            return public_url.rstrip('/')
        
        # Fallback to localhost (won't work with Twilio)
        from config import API_HOST, API_PORT
        fallback_url = f"http://{API_HOST}:{API_PORT}"
        logger.warning(f"⚠️  No Docker URL configured, using fallback: {fallback_url} (won't work with Twilio)")
        return fallback_url
    
    else:  # local
        # Priority 2a: Auto-query ngrok API to get public URL
        auto_ngrok_url = get_ngrok_url_from_api()
        if auto_ngrok_url:
            logger.info(f"🔗 Auto-connected to ngrok: {auto_ngrok_url}")
            return auto_ngrok_url
        
        # Priority 2b: Check NGROK_URL environment variable (manual setting)
        ngrok_url = os.getenv("NGROK_URL")
        if ngrok_url:
            logger.info(f"🌐 Using ngrok URL from NGROK_URL env var: {ngrok_url}")
            return ngrok_url.rstrip('/')
        
        # Fallback to localhost (won't work with Twilio, but good for testing)
        from config import API_HOST, API_PORT
        fallback_url = f"http://{API_HOST}:{API_PORT}"
        logger.warning(f"⚠️  Running locally without ngrok, using: {fallback_url} (won't work with Twilio)")
        logger.info("💡 Tip: Run 'ngrok http 4002' in another terminal - it will auto-detect!")
        logger.info("   Or set NGROK_URL in .env file")
        return fallback_url


def get_environment_info() -> dict:
    """Get detailed environment information for debugging"""
    import socket
    
    return {
        "detected_environment": detect_runtime_environment(),
        "hostname": socket.gethostname(),
        "kubernetes_service_host": os.getenv("KUBERNETES_SERVICE_HOST"),
        "pod_name": os.getenv("HOSTNAME") or os.getenv("POD_NAME"),
        "pod_namespace": os.getenv("POD_NAMESPACE"),
        "service_name": os.getenv("SERVICE_NAME"),
        "has_dockerenv": os.path.exists("/.dockerenv"),
        "has_k8s_token": os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"),
        "webhook_base_url": get_webhook_base_url(),
        "explicit_twilio_url": os.getenv("TWILIO_WEBHOOK_BASE_URL"),
        "ngrok_url": os.getenv("NGROK_URL"),
        "auto_detected_ngrok": get_ngrok_url_from_api(),
    }

