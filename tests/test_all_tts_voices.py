"""
Test all TTS voice options available during call registration.

This script tests all combinations of TTS models and voices to ensure they work correctly.
Following DEVELOPMENT_INSTRUCTIONS.md principles:
- Testing all features that are changed
- Comprehensive edge case testing
- No dummy data
"""

import sys
import os
import json
import requests
from datetime import datetime

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:4002")

# All TTS voices available in the UI (from /ui/app/page.tsx lines 2377-2382)
TTS_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

# All TTS models available in the UI (from /ui/app/page.tsx lines 2366-2367)
TTS_MODELS = ["tts-1", "tts-1-hd"]

# Test text
TEST_TEXT = "Hello, this is a test of the text to speech system. How do I sound?"

def test_tts_voice(voice: str, model: str, test_num: int, total_tests: int):
    """
    Test a specific TTS voice and model combination.
    
    Args:
        voice: TTS voice name
        model: TTS model name
        test_num: Current test number
        total_tests: Total number of tests
    
    Returns:
        dict: Test result with success status and details
    """
    print(f"\n[{test_num}/{total_tests}] Testing TTS Voice: {voice} with Model: {model}")
    print("-" * 70)
    
    try:
        # Prepare form data
        data = {
            "text": TEST_TEXT,
            "voice": voice,
            "model": model
        }
        
        # Make request to TTS API
        response = requests.post(
            f"{BASE_URL}/api/test/tts/synthesize-base64",
            data=data,
            timeout=30
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                audio_size = result.get("audio_size_bytes", 0)
                print(f"✅ SUCCESS")
                print(f"   - Voice: {result.get('voice')}")
                print(f"   - Model: {result.get('model')}")
                print(f"   - Audio Size: {audio_size} bytes")
                print(f"   - Timestamp: {result.get('timestamp')}")
                
                # Validate audio was actually generated
                if audio_size == 0:
                    print(f"⚠️  WARNING: Audio size is 0 bytes")
                    return {
                        "voice": voice,
                        "model": model,
                        "success": False,
                        "error": "Audio size is 0 bytes",
                        "status_code": 200
                    }
                
                return {
                    "voice": voice,
                    "model": model,
                    "success": True,
                    "audio_size": audio_size,
                    "status_code": 200
                }
            else:
                error = result.get("detail", "Unknown error")
                print(f"❌ FAILED: {error}")
                return {
                    "voice": voice,
                    "model": model,
                    "success": False,
                    "error": error,
                    "status_code": 200
                }
        else:
            error_text = response.text
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Error: {error_text}")
            return {
                "voice": voice,
                "model": model,
                "success": False,
                "error": f"HTTP {response.status_code}: {error_text}",
                "status_code": response.status_code
            }
            
    except requests.exceptions.Timeout:
        print(f"❌ FAILED: Request timeout (30s)")
        return {
            "voice": voice,
            "model": model,
            "success": False,
            "error": "Timeout after 30 seconds",
            "status_code": None
        }
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return {
            "voice": voice,
            "model": model,
            "success": False,
            "error": str(e),
            "status_code": None
        }

def main():
    """Main test function."""
    print("=" * 70)
    print("TTS VOICE AND MODEL TESTING")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Testing {len(TTS_VOICES)} voices × {len(TTS_MODELS)} models = {len(TTS_VOICES) * len(TTS_MODELS)} combinations")
    print(f"Test Text: \"{TEST_TEXT}\"")
    print("=" * 70)
    
    # Store all results
    results = []
    test_num = 0
    total_tests = len(TTS_VOICES) * len(TTS_MODELS)
    
    # Test all combinations
    for model in TTS_MODELS:
        for voice in TTS_VOICES:
            test_num += 1
            result = test_tts_voice(voice, model, test_num, total_tests)
            results.append(result)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"\n✅ Successful: {len(successful)}/{total_tests}")
    print(f"❌ Failed: {len(failed)}/{total_tests}")
    
    if failed:
        print("\n❌ FAILED TESTS:")
        print("-" * 70)
        for i, result in enumerate(failed, 1):
            print(f"{i}. {result['voice']} + {result['model']}")
            print(f"   Error: {result['error']}")
            print(f"   Status Code: {result['status_code']}")
    
    if successful:
        print("\n✅ SUCCESSFUL TESTS:")
        print("-" * 70)
        for i, result in enumerate(successful, 1):
            print(f"{i}. {result['voice']} + {result['model']} - {result.get('audio_size', 0)} bytes")
    
    # Save detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/Users/tejaraognadra/voiceagent/tests/tts_test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "successful": len(successful),
            "failed": len(failed),
            "results": results
        }, f, indent=2)
    
    print(f"\n📝 Detailed results saved to: {results_file}")
    
    # Exit with error code if any tests failed
    if failed:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        sys.exit(1)
    else:
        print("\n🎉 All TTS voice and model combinations are working correctly!")
        sys.exit(0)

if __name__ == "__main__":
    main()
