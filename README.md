# Samana Rate Limit Testing Tool

A powerful tool for testing and analyzing rate limiting mechanisms in web applications, specifically designed for testing Citrix Gateway rate limiting features. This script helps identify rate limit thresholds, time windows, and response patterns by simulating various request patterns.

## Features

- Multiple predefined test profiles for different scenarios
- Custom rate limit testing with threshold and timeslice parameters
- Progress bar for real-time monitoring
- Comprehensive test summary and analysis
- Multi-threaded and sequential testing modes
- Detailed logging and results saving in a dedicated results folder

## Repository Information

- GitHub Repository: [https://github.com/juandiab/samana_rate_limit_test.git](https://github.com/juandiab/samana_rate_limit_test.git)
- License: GPL-3.0
- Author: Juan Pablo Otalvaro

## Prerequisites

- Python 3.6 or higher
- Required packages:
  - requests
  - tqdm

## Installation

1. Clone the repository:
```bash
git clone https://github.com/juandiab/samana_rate_limit_test.git
cd samana_rate_limit_test
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

3. Install required packages:
```bash
pip install requests tqdm
```

## Usage

Basic usage:
```bash
source venv/bin/activate && python samana_rate_limit_test.py --hostname gateway.samana.cloud --speed slow_rate
```

### Required Arguments

- `--hostname`: Target hostname to test (e.g., gateway.samana.cloud)
- `--speed`: Test speed profile (see available profiles below)

### Available Speed Profiles

1. **slow_brute_force**
   - 20 attempts over 10 minutes
   - 30 seconds delay between attempts
   - Sequential testing
   - Best for: Testing long-term rate limits

2. **slow_rate**
   - 6 attempts over 1 minute
   - 8 seconds delay between attempts
   - Sequential testing
   - Best for: Testing moderate rate limits

3. **high_rate**
   - 10 attempts over 30 seconds
   - 3 seconds delay between attempts
   - 2 threads
   - Best for: Testing frequent request limits

4. **fast_rate**
   - 5 attempts in 2 seconds
   - 0.4 seconds delay between attempts
   - 2 threads
   - Best for: Testing quick burst limits

5. **ultra_high_rate**
   - 150 attempts in 5 seconds
   - 0.05 seconds delay between attempts
   - 5 threads
   - Best for: Testing extreme burst limits

6. **custom_rate**
   - Customizable threshold and timeslice
   - Automatically calculates optimal delay
   - Example:
     ```bash
     python samana_rate_limit_test.py --hostname gateway.samana.cloud --speed custom_rate --threshold 10 --timeslice 60
     ```
   - This tests 10 requests per minute limit

### Custom Parameters

For the `custom_rate` profile, you can specify:
- `--threshold`: Number of requests allowed in the timeslice
- `--timeslice`: Time window in seconds

For other profiles, you can override default parameters with:
- `--attempts`: Custom number of attempts
- `--timeframe`: Custom timeframe in seconds
- `--delay`: Custom delay between attempts
- `--threads`: Custom number of threads

## Output

The script provides:
1. Real-time progress bar showing:
   - Overall progress
   - Current status
   - Total requests
   - Successful requests

2. Test summary showing:
   - Total requests
   - Successful requests
   - Success rate
   - Rate limit analysis (if detected)
   - Timing analysis

3. Results file:
   - Saved in the `results` directory
   - Filename format: `rate_limit_test_YYYYMMDD_HHMMSS.txt`
   - Contains detailed test configuration and results
   - The `results` directory is automatically created if it doesn't exist

## Example Output

```
Starting test with parameters:
Speed: slow_rate
Attempts: 6
Timeframe: 60 seconds
Delay between attempts: 8 seconds
Mode: Sequential

Testing Progress: 100%|██████████| 6/6 [00:48<00:00,  8.03s/it, Status=unknown, Total=6, Success=0]

================================================================================
TEST SUMMARY
================================================================================
Total Requests: 6
Successful Requests: 0
Success Rate: 0.00%

Timing Analysis:
First failure occurred at: 0.12 seconds
Requests before first failure: 0
================================================================================

Results saved to: results/rate_limit_test_20250424_164117.txt
```

## Best Practices

1. Always test in a controlled environment
2. Start with slower rates and gradually increase
3. Monitor system resources during testing
4. Review the detailed results file for analysis
5. Use custom_rate for specific rate limit testing
6. Check the `results` directory for historical test data

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details. 