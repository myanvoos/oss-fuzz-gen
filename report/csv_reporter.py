import csv
import json
import logging
import os
from typing import Dict, List, Optional

class CSVReporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def add_benchmark_crashes(self, benchmark_id: str, crash_json_path: str):
        """Convert crash.json to CSV format for easy viewing/downloading"""
        logging.info(f"Adding benchmark crashes for {benchmark_id} from {crash_json_path}")
        
        try:
            # Check if the file exists
            if not os.path.exists(crash_json_path):
                logging.error(f"File does not exist: {crash_json_path}")
                return
            
            # Read the file content
            with open(crash_json_path, 'r') as f:
                crash_data = json.load(f)
            
            # Create CSV file path
            csv_path = os.path.join(self.output_dir, f'benchmark/{benchmark_id}/crashes.csv')
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            # Extract samples
            samples = crash_data.get('samples', [])
            logging.info(f"Found {len(samples)} samples in crash data")
            
            if not samples:
                logging.warning(f"No samples to add for benchmark {benchmark_id}")
                return
                
            # Write to CSV
            with open(csv_path, 'w', newline='') as csvfile:
                fieldnames = [
                    "Benchmark", "Sample", "Status", "Compiles", "Crashes", 
                    "Crash Reason", "Bug", "Triage", "Coverage", "Coverage Diff",
                    "Stacktrace", "Target Binary", "Model"
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for sample in samples:
                    row = {
                        "Benchmark": sample.get('benchmark', ''),
                        "Sample": sample.get('sample', ''),
                        "Status": sample.get('status', ''),
                        "Compiles": sample.get('compiles', ''),
                        "Crashes": sample.get('crashes', ''),
                        "Crash Reason": sample.get('crash_reason', ''),
                        "Bug": sample.get('bug', ''),
                        "Triage": sample.get('triage', ''),
                        "Coverage": sample.get('coverage', ''),
                        "Coverage Diff": sample.get('coverage_diff', ''),
                        "Stacktrace": sample.get('stacktrace', '')[:1000] if sample.get('stacktrace') else '',
                        "Target Binary": sample.get('target_binary', ''),
                        "Model": sample.get('model', '')
                    }
                    writer.writerow(row)
                
            logging.info(f"Created CSV file at {csv_path}")
            return csv_path
            
        except Exception as e:
            logging.error(f"Error adding benchmark crashes to CSV: {e}")
            import traceback
            traceback.print_exc()
            return None 