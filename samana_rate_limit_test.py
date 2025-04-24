"""
Rate Limit Testing Script
========================

Created by Juan Pablo Otalvaro for SamanaGroup LLC.
Copyright 2025 SamanaGroup LLC. All rights reserved.

This script is designed for testing rate limiting mechanisms using multi-threading
and command-line arguments. It helps analyze rate limiting patterns by tracking
request success/failure patterns and timing information.

Usage:
    Configure the desired test profile and run against target system to analyze
    rate limiting behavior, thresholds, and time windows.

License: Proprietary - Unauthorized use, modification, or distribution is prohibited.
"""

import argparse
import requests
import threading
import time
import urllib3
from datetime import datetime
import random
import sys
import os
from typing import Dict, List, Optional
from tqdm import tqdm
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RateLimitTester:
    # Predefined speed parameters
    SPEED_PARAMETERS = {
        "slow_brute_force": {
            "attempts": 20,
            "timeframe": 600,  # 10 minutes
            "delay": 30,       # 30 seconds between attempts
            "threads": 1,
            "description": "Slow brute force attack (20 attempts over 10 minutes)",
            "sequential": True
        },
        "slow_rate": {
            "attempts": 6,
            "timeframe": 60,   # 1 minute
            "delay": 8,        # 6 seconds between attempts
            "threads": 1,
            "description": "Slow rate (10 attempts over 1 minute)",
            "sequential": True
        },
        "high_rate": {
            "attempts": 10,
            "timeframe": 30,   # 30 seconds
            "delay": 3,        # 3 seconds between attempts
            "threads": 2,
            "description": "High frequency attempts (10 in 30 seconds)",
            "sequential": True
        },
        "fast_rate": {
            "attempts": 5,
            "timeframe": 2,    # 2 seconds
            "delay": 0.4,      # 0.4 seconds between attempts
            "threads": 2,
            "description": "Fast rate (5 attempts in 2 seconds)",
            "sequential": True
        },
        "ultra_high_rate": {
            "attempts": 150,
            "timeframe": 5,    # 5 seconds
            "delay": 0.05,     # 0.05 seconds between attempts
            "threads": 5,
            "description": "Ultra high frequency attempts (150 in 5 seconds)",
            "sequential": False
        }
    }

    # Response patterns to scan for
    RESPONSE_PATTERNS = {
        "success": ["success", "authenticated", "login successful"],
        "failure": ["failure", "invalid", "error", "denied"],
        "rate_limit": ["rate limit", "too many requests", "429", "blocked", "unusual rate"],
        "dropped": ["connection refused", "connection reset", "timeout"]
    }

    def __init__(self, hostname: str, speed: str, custom_params: Optional[Dict] = None):
        self.hostname = hostname
        self.path = "/nf/auth/doAuthentication.do"
        self.url = f"https://{self.hostname}{self.path}"
        self.speed = speed
        self.custom_params = custom_params
        self.results = []
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        
        # Create results directory if it doesn't exist
        self.results_dir = "results"
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Rate limit detection counters
        self.start_time = None
        self.rate_limit_detected_time = None
        self.total_requests = 0
        self.successful_requests = 0
        self.rate_limit_threshold_requests = 0
        self.rate_limit_detected = False
        
        # Enhanced timing analysis
        self.first_failure_time = None
        self.consecutive_failures = 0
        self.last_success_time = None
        self.failure_sequences = []  # Track failure sequences
        self.success_sequences = []  # Track success sequences

        # Headers (simulate browser)
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    def get_test_parameters(self) -> Dict:
        """Get test parameters based on speed or custom parameters"""
        if self.speed == "custom" and self.custom_params:
            return self.custom_params
        return self.SPEED_PARAMETERS.get(self.speed, self.SPEED_PARAMETERS["high_rate"])

    def scan_response(self, response_text: str) -> str:
        """Scan response for patterns and return the detected status"""
        response_text = response_text.lower()
        for status, patterns in self.RESPONSE_PATTERNS.items():
            if any(pattern in response_text for pattern in patterns):
                return status
        return "unknown"

    def track_request_sequence(self, status: str, current_time: datetime):
        """Track sequences of successes and failures"""
        elapsed = (current_time - self.start_time).total_seconds()
        
        if status == "success":
            self.last_success_time = current_time
            self.consecutive_failures = 0
            self.success_sequences.append({
                'time': current_time,
                'elapsed': elapsed,
                'total_requests': self.total_requests
            })
        else:
            if self.first_failure_time is None:
                self.first_failure_time = current_time
            
            self.consecutive_failures += 1
            if self.consecutive_failures == 1:  # Start of a new failure sequence
                self.failure_sequences.append({
                    'start_time': current_time,
                    'elapsed': elapsed,
                    'total_requests': self.total_requests
                })

    def make_request(self, thread_id: int, params: Dict):
        """Make HTTP requests in a thread"""
        payload = {
            "login": f"testuser{thread_id}",
            "passwd": f"testuser{thread_id}",
            "passwd1": "",
            "otpmanualentry": "false",
            "otppush": "true",
            "passwdreset": "0",
            "Logon": "Submit",
            "StateContext": ""
        }

        for i in range(params["attempts"]):
            if self.stop_event.is_set():
                break

            try:
                with self.lock:
                    self.total_requests += 1
                    current_total = self.total_requests

                response = requests.post(
                    self.url,
                    data=payload,
                    headers=self.headers,
                    verify=False,
                    timeout=5
                )
                
                status = self.scan_response(response.text)
                current_time = datetime.now()
                elapsed_seconds = (current_time - self.start_time).total_seconds()

                with self.lock:
                    if status == "success":
                        self.successful_requests += 1
                    
                    self.track_request_sequence(status, current_time)

                    if (status == "rate_limit" or status == "dropped") and not self.rate_limit_detected:
                        self.rate_limit_detected = True
                        self.rate_limit_detected_time = current_time
                        self.rate_limit_threshold_requests = current_total
                        elapsed = (current_time - self.start_time).total_seconds()
                        self.stop_event.set()

                result = {
                    'time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'thread': thread_id,
                    'attempt': i + 1,
                    'status': status,
                    'elapsed_seconds': f"{elapsed_seconds:.2f}",
                    'total_requests': current_total,
                    'http_status': response.status_code,
                    'response_text': response.text[:100].replace('\n', ' ')
                }

                with self.lock:
                    self.results.append(result)

                time.sleep(params["delay"] + random.uniform(-0.1, 0.1))

            except requests.exceptions.ConnectionError as e:
                with self.lock:
                    self.total_requests += 1
                    current_total = self.total_requests
                    current_time = datetime.now()
                    elapsed_seconds = (current_time - self.start_time).total_seconds()
                    
                    if not self.rate_limit_detected:
                        self.rate_limit_detected = True
                        self.rate_limit_detected_time = current_time
                        self.rate_limit_threshold_requests = current_total
                        self.stop_event.set()

                    self.results.append({
                        'time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'thread': thread_id,
                        'attempt': i + 1,
                        'status': 'dropped',
                        'elapsed_seconds': f"{elapsed_seconds:.2f}",
                        'total_requests': current_total,
                        'http_status': 0,
                        'response_text': "Connection dropped/refused"
                    })
                time.sleep(params["delay"])

            except requests.exceptions.Timeout as e:
                with self.lock:
                    self.total_requests += 1
                    current_total = self.total_requests
                    current_time = datetime.now()
                    elapsed_seconds = (current_time - self.start_time).total_seconds()
                    
                    if not self.rate_limit_detected:
                        self.rate_limit_detected = True
                        self.rate_limit_detected_time = current_time
                        self.rate_limit_threshold_requests = current_total
                        self.stop_event.set()

                    self.results.append({
                        'time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'thread': thread_id,
                        'attempt': i + 1,
                        'status': 'dropped',
                        'elapsed_seconds': f"{elapsed_seconds:.2f}",
                        'total_requests': current_total,
                        'http_status': 0,
                        'response_text': "Request timeout"
                    })
                time.sleep(params["delay"])

            except Exception as e:
                with self.lock:
                    self.total_requests += 1
                    current_total = self.total_requests
                    current_time = datetime.now()
                    elapsed_seconds = (current_time - self.start_time).total_seconds()
                    self.results.append({
                        'time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'thread': thread_id,
                        'attempt': i + 1,
                        'status': 'error',
                        'elapsed_seconds': f"{elapsed_seconds:.2f}",
                        'total_requests': current_total,
                        'http_status': 0,
                        'response_text': str(e)[:100]
                    })
                time.sleep(params["delay"])

    def run_sequential_test(self, params: Dict):
        """Run a sequential test with a single thread"""
        print(f"\nRunning sequential test with parameters:")
        print(f"Attempts: {params['attempts']}")
        print(f"Timeframe: {params['timeframe']} seconds")
        print(f"Delay between attempts: {params['delay']} seconds\n")

        self.start_time = datetime.now()
        last_request_time = None

        with tqdm(total=params["attempts"], desc="Testing Progress") as pbar:
            for i in range(params["attempts"]):
                if self.stop_event.is_set():
                    break

                # Ensure minimum delay between attempts
                if last_request_time:
                    elapsed_since_last = (datetime.now() - last_request_time).total_seconds()
                    if elapsed_since_last < params["delay"]:
                        sleep_time = params["delay"] - elapsed_since_last
                        time.sleep(sleep_time)

                try:
                    self.total_requests += 1
                    current_total = self.total_requests
                    last_request_time = datetime.now()

                    response = requests.post(
                        self.url,
                        data={
                            "login": "testuser1",
                            "passwd": "testuser1",
                            "passwd1": "",
                            "otpmanualentry": "false",
                            "otppush": "true",
                            "passwdreset": "0",
                            "Logon": "Submit",
                            "StateContext": ""
                        },
                        headers=self.headers,
                        verify=False,
                        timeout=5,
                        allow_redirects=False
                    )
                    
                    redirect_count = 0
                    while response.status_code in [301, 302, 303, 307, 308]:
                        redirect_count += 1
                        redirect_url = response.headers.get('Location')
                        if not redirect_url:
                            break
                        
                        response = requests.get(
                            redirect_url,
                            headers=self.headers,
                            verify=False,
                            timeout=5,
                            allow_redirects=False
                        )
                    
                    status = self.scan_response(response.text)
                    current_time = datetime.now()
                    elapsed_seconds = (current_time - self.start_time).total_seconds()

                    if status == "success":
                        self.successful_requests += 1
                    
                    self.track_request_sequence(status, current_time)

                    if (status == "rate_limit" or status == "dropped") and not self.rate_limit_detected:
                        self.rate_limit_detected = True
                        self.rate_limit_detected_time = current_time
                        self.rate_limit_threshold_requests = current_total
                        self.stop_event.set()

                    result = {
                        'time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'thread': 1,
                        'attempt': i + 1,
                        'status': status,
                        'elapsed_seconds': f"{elapsed_seconds:.2f}",
                        'total_requests': current_total,
                        'http_status': response.status_code,
                        'response_text': response.text[:100].replace('\n', ' '),
                        'redirect_count': redirect_count
                    }

                    self.results.append(result)
                    pbar.update(1)
                    pbar.set_postfix({
                        'Status': status,
                        'Total': current_total,
                        'Success': self.successful_requests
                    })

                    if status == "rate_limit":
                        self.stop_event.set()
                        break

                    time.sleep(max(0.1, params["delay"] + random.uniform(-0.1, 0.1)))

                except requests.exceptions.ConnectionError as e:
                    self.total_requests += 1
                    current_total = self.total_requests
                    current_time = datetime.now()
                    elapsed_seconds = (current_time - self.start_time).total_seconds()
                    
                    if not self.rate_limit_detected:
                        self.rate_limit_detected = True
                        self.rate_limit_detected_time = current_time
                        self.rate_limit_threshold_requests = current_total
                        self.stop_event.set()

                    self.results.append({
                        'time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'thread': 1,
                        'attempt': i + 1,
                        'status': 'dropped',
                        'elapsed_seconds': f"{elapsed_seconds:.2f}",
                        'total_requests': current_total,
                        'http_status': 0,
                        'response_text': "Connection dropped/refused"
                    })
                    pbar.update(1)
                    time.sleep(params["delay"])

                except requests.exceptions.Timeout as e:
                    self.total_requests += 1
                    current_total = self.total_requests
                    current_time = datetime.now()
                    elapsed_seconds = (current_time - self.start_time).total_seconds()
                    
                    if not self.rate_limit_detected:
                        self.rate_limit_detected = True
                        self.rate_limit_detected_time = current_time
                        self.rate_limit_threshold_requests = current_total
                        self.stop_event.set()

                    self.results.append({
                        'time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'thread': 1,
                        'attempt': i + 1,
                        'status': 'dropped',
                        'elapsed_seconds': f"{elapsed_seconds:.2f}",
                        'total_requests': current_total,
                        'http_status': 0,
                        'response_text': "Request timeout"
                    })
                    pbar.update(1)
                    time.sleep(params["delay"])

                except Exception as e:
                    self.total_requests += 1
                    current_total = self.total_requests
                    current_time = datetime.now()
                    elapsed_seconds = (current_time - self.start_time).total_seconds()
                    self.results.append({
                        'time': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'thread': 1,
                        'attempt': i + 1,
                        'status': 'error',
                        'elapsed_seconds': f"{elapsed_seconds:.2f}",
                        'total_requests': current_total,
                        'http_status': 0,
                        'response_text': str(e)[:100]
                    })
                    pbar.update(1)
                    time.sleep(params["delay"])

    def save_results(self):
        """Save test results to a file in the results directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rate_limit_test_{timestamp}.txt"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write("="*120 + "\n")
            f.write("SamanaGroup LLC - Rate Limit Testing Results\n")
            f.write("Created by Juan Pablo Otalvaro\n")
            f.write("Copyright 2025 SamanaGroup LLC. All rights reserved.\n")
            f.write("="*120 + "\n\n")
            
            f.write("Test Configuration:\n")
            f.write("-"*40 + "\n")
            f.write(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Hostname: {self.hostname}\n")
            f.write(f"Speed: {self.speed}\n")
            
            if self.rate_limit_detected:
                f.write("\nRate Limit Analysis:\n")
                f.write("-"*40 + "\n")
                elapsed = (self.rate_limit_detected_time - self.start_time).total_seconds()
                f.write(f"Rate limit detected after: {elapsed:.2f} seconds\n")
                f.write(f"Total requests at detection: {self.rate_limit_threshold_requests}\n")
                f.write(f"Successful requests before limit: {self.successful_requests}\n")
                f.write(f"Requests per second: {self.rate_limit_threshold_requests/elapsed:.2f}\n")
            
            f.write("\nTiming Analysis:\n")
            f.write("-"*40 + "\n")
            if self.first_failure_time:
                first_failure_elapsed = (self.first_failure_time - self.start_time).total_seconds()
                f.write(f"First failure occurred at: {first_failure_elapsed:.2f} seconds\n")
                f.write(f"Requests before first failure: {len(self.success_sequences)}\n")
            
            if self.last_success_time:
                last_success_elapsed = (self.last_success_time - self.start_time).total_seconds()
                f.write(f"Last successful request at: {last_success_elapsed:.2f} seconds\n")
            
            if self.failure_sequences:
                f.write("\nFailure Sequences:\n")
                for i, seq in enumerate(self.failure_sequences, 1):
                    f.write(f"Sequence {i}: Started at {seq['elapsed']:.2f}s "
                           f"(Request #{seq['total_requests']})\n")
            
            if self.success_sequences:
                f.write("\nSuccess Sequences:\n")
                for i, seq in enumerate(self.success_sequences, 1):
                    f.write(f"Success {i}: At {seq['elapsed']:.2f}s "
                           f"(Request #{seq['total_requests']})\n")
            
            f.write("\nDetailed Test Results:\n")
            f.write("-"*40 + "\n")
            f.write(f"{'Time':<20} {'Thread':<8} {'Attempt':<8} {'Status':<10} {'Elapsed(s)':<10} {'Total':<8} "
                   f"{'HTTP':<6} {'Response Text':<50} {'Redirects':<10}\n")
            f.write("-"*120 + "\n")
            
            for result in self.results:
                f.write(f"{result['time']:<20} {result['thread']:<8} {result['attempt']:<8} "
                       f"{result['status']:<10} {result['elapsed_seconds']:<10} {result['total_requests']:<8} "
                       f"{result['http_status']:<6} {result['response_text']:<50} {result['redirect_count']:<10}\n")
            
            f.write("-"*120 + "\n")
            f.write(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*120 + "\n")
        
        print(f"\nResults saved to: {filepath}")

    def run_test(self):
        """Run the rate limit test"""
        params = self.get_test_parameters()

        print(f"\nStarting test with parameters:")
        print(f"Speed: {self.speed}")
        print(f"Attempts: {params['attempts']}")
        print(f"Timeframe: {params['timeframe']} seconds")
        print(f"Delay between attempts: {params['delay']} seconds")
        print(f"Mode: {'Sequential' if params['sequential'] else 'Multi-threaded'}\n")

        if params['sequential']:
            self.run_sequential_test(params)
        else:
            threads = []
            self.start_time = datetime.now()
            
            with tqdm(total=params["attempts"] * params["threads"], desc="Testing Progress") as pbar:
                for i in range(params["threads"]):
                    thread = threading.Thread(
                        target=self.make_request,
                        args=(i + 1, params)
                    )
                    threads.append(thread)
                    thread.start()

                while any(thread.is_alive() for thread in threads):
                    time.sleep(0.1)
                    pbar.n = self.total_requests
                    pbar.set_postfix({
                        'Total': self.total_requests,
                        'Success': self.successful_requests
                    })
                    pbar.refresh()

                for thread in threads:
                    thread.join(timeout=params["timeframe"])

        # Display test summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Requests: {self.total_requests}")
        print(f"Successful Requests: {self.successful_requests}")
        print(f"Success Rate: {(self.successful_requests/self.total_requests)*100:.2f}%")
        
        if self.rate_limit_detected:
            elapsed = (self.rate_limit_detected_time - self.start_time).total_seconds()
            print("\nRate Limit Analysis:")
            print(f"Rate limit detected after: {elapsed:.2f} seconds")
            print(f"Total requests at detection: {self.rate_limit_threshold_requests}")
            print(f"Requests per second: {self.rate_limit_threshold_requests/elapsed:.2f}")
        
        print("\nTiming Analysis:")
        if self.first_failure_time:
            first_failure_elapsed = (self.first_failure_time - self.start_time).total_seconds()
            print(f"First failure occurred at: {first_failure_elapsed:.2f} seconds")
            print(f"Requests before first failure: {len(self.success_sequences)}")
        
        if self.last_success_time:
            last_success_elapsed = (self.last_success_time - self.start_time).total_seconds()
            print(f"Last successful request at: {last_success_elapsed:.2f} seconds")
        
        print("="*80)

        # Save results
        self.save_results()

def main():
    parser = argparse.ArgumentParser(description='Rate Limit Testing Tool')
    parser.add_argument('--hostname', required=True, help='Target hostname')
    parser.add_argument('--speed', required=True, 
                      choices=['slow_brute_force', 'slow_rate', 'high_rate', 'fast_rate', 'ultra_high_rate', 'custom_rate'],
                      help='Test speed profile')
    parser.add_argument('--threshold', type=int, help='Custom rate limit threshold (required for custom_rate)')
    parser.add_argument('--timeslice', type=int, help='Custom rate limit timeslice in seconds (required for custom_rate)')
    parser.add_argument('--attempts', type=int, help='Custom number of attempts')
    parser.add_argument('--timeframe', type=int, help='Custom timeframe in seconds')
    parser.add_argument('--delay', type=float, help='Custom delay between attempts')
    parser.add_argument('--threads', type=int, help='Custom number of threads')

    args = parser.parse_args()

    custom_params = None
    if args.speed == "custom_rate":
        if not all([args.threshold, args.timeslice]):
            print("Error: custom_rate requires --threshold and --timeslice parameters")
            sys.exit(1)
        
        # Calculate delay based on threshold and timeslice
        delay = args.timeslice / args.threshold
        attempts = args.threshold * 2  # Test with double the threshold
        timeframe = args.timeslice * 2  # Test over double the timeslice
        
        custom_params = {
            "attempts": attempts,
            "timeframe": timeframe,
            "delay": delay,
            "threads": 1,
            "description": f"Custom rate test (threshold: {args.threshold} requests per {args.timeslice} seconds)",
            "sequential": True
        }
    elif args.speed == "custom":
        if not all([args.attempts, args.timeframe, args.delay, args.threads]):
            print("Error: Custom speed requires --attempts, --timeframe, --delay, and --threads")
            sys.exit(1)
        custom_params = {
            "attempts": args.attempts,
            "timeframe": args.timeframe,
            "delay": args.delay,
            "threads": args.threads,
            "description": "Custom test parameters"
        }

    tester = RateLimitTester(args.hostname, args.speed, custom_params)
    tester.run_test()

if __name__ == "__main__":
    main() 