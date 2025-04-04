import gspread
import json
import logging
import os
import sys
from typing import Dict, List, Optional

class SheetsReporter:
    def __init__(self, sheet_name: str = "Fuzzing Results", service_account_file: Optional[str] = None, 
                 share_with_email: Optional[str] = None):
        self.sheet_name = sheet_name
        self.service_account_file = service_account_file or os.path.expanduser("~/Downloads/oss-fuzz-gen.json")
        self.share_with_email = share_with_email
        
        # Configure logging to ensure messages are displayed
        logging.basicConfig(level=logging.INFO, 
                           format='%(asctime)s - %(levelname)s - %(message)s',
                           stream=sys.stdout)
        
        print(f"\n\n==== GOOGLE SHEETS INTEGRATION ====")
        print(f"Using service account file: {self.service_account_file}")
        
        try:
            self.gc = gspread.service_account(filename=self.service_account_file)
            print("Successfully authenticated with service account")
            self.sheet = self._create_or_get_sheet()
            self._setup_headers()
        except Exception as e:
            print(f"ERROR initializing Google Sheets: {str(e)}")
            raise
        
    def _create_or_get_sheet(self):
        try:
            sheet = self.gc.open(self.sheet_name)
            print(f"Found existing sheet: {self.sheet_name}")
            print(f"SHEET URL: https://docs.google.com/spreadsheets/d/{sheet.id}")
            
            # Share the sheet if an email is provided
            if self.share_with_email:
                self._share_sheet(sheet)
                
            return sheet
        except gspread.SpreadsheetNotFound:
            print(f"Creating new sheet: {self.sheet_name}")
            sheet = self.gc.create(self.sheet_name)
            
            # Get the email from service account file to display in logs
            with open(self.service_account_file, 'r') as f:
                service_info = json.load(f)
                client_email = service_info.get('client_email', 'unknown')
            
            print(f"Created new Google Sheet: {self.sheet_name}")
            print(f"SHEET ID: {sheet.id}")
            print(f"SHEET URL: https://docs.google.com/spreadsheets/d/{sheet.id}")
            print(f"Sheet is owned by service account: {client_email}")
            
            # Share the sheet if an email is provided
            if self.share_with_email:
                self._share_sheet(sheet)
            else:
                print("IMPORTANT: No email provided for sharing. You need to manually share the sheet.")
                print(f"The service account ({client_email}) needs to share the sheet with you")
            
            return sheet
    
    def _share_sheet(self, sheet):
        """Share the sheet with the provided email address."""
        try:
            sheet.share(self.share_with_email, perm_type='user', role='writer')
            print(f"Successfully shared sheet with {self.share_with_email}")
        except Exception as e:
            print(f"ERROR sharing sheet: {str(e)}")
    
    def _setup_headers(self):
        worksheet = self.sheet.sheet1
        headers = [
            "Benchmark", "Sample", "Status", "Compiles", "Crashes", 
            "Crash Reason", "Bug", "Triage", "Coverage", "Coverage Diff",
            "Stacktrace", "Target Binary", "Model"
        ]
        worksheet.update('A1:M1', [headers])
        worksheet.format('A1:M1', {'textFormat': {'bold': True}})
        print("Sheet headers set up successfully")
        
    def add_benchmark_crashes(self, benchmark_id: str, crash_json_path: str):
        print(f"Adding benchmark crashes for {benchmark_id} from {crash_json_path}")
        try:
            # Check if the file exists
            if not os.path.exists(crash_json_path):
                print(f"ERROR: File does not exist: {crash_json_path}")
                return
            
            # Read the file content
            with open(crash_json_path, 'r') as f:
                file_content = f.read()
                print(f"File content length: {len(file_content)} bytes")
            
            # Try to parse JSON
            try:
                crash_data = json.loads(file_content)
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON in file: {e}")
                print(f"First 200 characters of file: {file_content[:200]}")
                return
        
            # Check if samples exist in the data
            if 'samples' not in crash_data:
                print(f"ERROR: No 'samples' key in crash data. Keys found: {list(crash_data.keys())}")
                return
            
            samples = crash_data.get('samples', [])
            print(f"Found {len(samples)} samples in crash data")
            
            rows = []
            for i, sample in enumerate(samples):
                print(f"Processing sample {i+1}/{len(samples)}")
                row = [
                    sample.get('benchmark', ''),
                    sample.get('sample', ''),
                    sample.get('status', ''),
                    sample.get('compiles', ''),
                    sample.get('crashes', ''),
                    sample.get('crash_reason', ''),
                    sample.get('bug', ''),
                    sample.get('triage', ''),
                    sample.get('coverage', ''),
                    sample.get('coverage_diff', ''),
                    sample.get('stacktrace', '')[:1000] if sample.get('stacktrace') else '',
                    sample.get('target_binary', ''),
                    sample.get('model', '')
                ]
                rows.append(row)
            
            if rows:
                worksheet = self.sheet.sheet1
                next_row = len(worksheet.get_all_values()) + 1
                print(f"Updating sheet starting at row {next_row}")
                worksheet.update(f'A{next_row}:M{next_row + len(rows) - 1}', rows)
                print(f"Added {len(rows)} rows for benchmark {benchmark_id} to Google Sheet")
                print(f"SHEET URL: https://docs.google.com/spreadsheets/d/{self.sheet.id}")
            else:
                print(f"No rows to add for benchmark {benchmark_id}")
        except Exception as e:
            print(f"ERROR adding benchmark crashes: {str(e)}")
            import traceback
            traceback.print_exc() 