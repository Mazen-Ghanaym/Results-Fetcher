from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import requests
import hashlib
import time
import random
import string
import tempfile
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import pandas as pd

load_dotenv() 

API_KEY = os.getenv("CODEFORCES_API_KEY")
API_SECRET = os.getenv("CODEFORCES_API_SECRET")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

class CodeforcesAPI:
    """
    A client for the Codeforces API.

    Handles both anonymous and authenticated requests, including the generation
    of the required apiSig for authorized calls.
    """
    BASE_URL = "https://codeforces.com/api/"
    # Respect the API rate limit of 1 call per 2 seconds.
    REQUEST_INTERVAL = 2

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initializes the API client.

        Args:
            api_key: Your Codeforces API key.
            api_secret: Your Codeforces API secret.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.last_request_time = 0

    def _generate_api_sig(self, method_name: str, params: Dict[str, Any]) -> str:
        """
        Generates the apiSig required for authenticated requests.

        Args:
            method_name: The name of the API method being called.
            params: A dictionary of parameters for the API call.

        Returns:
            The generated apiSig string.
        """
        # 1. Create a sorted list of "key=value" strings from the parameters.
        # The parameters must be sorted lexicographically.
        param_list = sorted(params.items())
        param_string = "&".join([f"{key}={value}" for key, value in param_list])

        # 2. Generate a 6-character random string.
        rand_prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

        # 3. Form the string to be hashed.
        # format: <rand>/<methodName>?<params>#<secret>
        hash_string = f"{rand_prefix}/{method_name}?{param_string}#{self.api_secret}".encode('utf-8')

        # 4. Calculate the SHA-512 hash.
        sha512_hash = hashlib.sha512(hash_string).hexdigest()

        # 5. The final apiSig is the random prefix + the hash.
        return f"{rand_prefix}{sha512_hash}"

    def _make_request(self, method_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Makes a request to the Codeforces API.

        Args:
            method_name: The name of the API method.
            params: A dictionary of parameters.

        Returns:
            The JSON response from the API as a dictionary.
        """
        if params is None:
            params = {}

        # Respect the rate limit.
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.REQUEST_INTERVAL:
            time.sleep(self.REQUEST_INTERVAL - time_since_last_request)
        
        # Check if this is an authenticated request.
        if self.api_key and self.api_secret:
            params['apiKey'] = self.api_key
            params['time'] = int(time.time())
            params['apiSig'] = self._generate_api_sig(method_name, params)

        try:
            response = requests.get(self.BASE_URL + method_name, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            self.last_request_time = time.time()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "FAILED", "comment": f"HTTP Request failed: {e}"}

    def get_contest_standings(self, contest_id: int, from_rank: int = -1, count: int = -1, show_unofficial: bool = False) -> Dict[str, Any]:
        """
        Fetches contest standings.
        
        Args:
            contest_id: The contest ID.
            from_rank: Starting rank position.
            count: Number of standings to return.
            show_unofficial: Whether to show unofficial participants.
            
        Returns:
            The JSON response from the API.
        """
        params = {
            "contestId": contest_id,
        }
        if from_rank != -1:
            params["from"] = from_rank
        if count != -1:
            params["count"] = count
        if show_unofficial:
            params["showUnofficial"] = str(show_unofficial).lower()
        return self._make_request("contest.standings", params)

def process_contest_data(contest_id: int, handles_text: str) -> str:
    """
    Process contest data and generate Excel file.
    
    Args:
        contest_id: The contest ID to fetch standings from
        handles_text: Text containing handles (one per line)
        
    Returns:
        Path to the generated Excel file
    """
    # Initialize API client
    api_key = API_KEY
    api_secret = API_SECRET

    if api_key and api_secret:
        api_client = CodeforcesAPI(api_key=api_key, api_secret=api_secret)
    else:
        api_client = CodeforcesAPI()
    
    # Get contest standings
    standings = api_client.get_contest_standings(contest_id=contest_id, show_unofficial=True)
    contestants = {}
    
    if standings.get("status") == "OK":
        for contestant in standings['result']['rows']:
            contestants[contestant['party']['members'][0]['handle']] = contestant['points']
    else:
        raise Exception(f"Failed to get standings: {standings.get('comment', 'No comment provided.')}")
    
    # Process handles
    data = []
    
    lines = handles_text.split('\n')

    for i, line in enumerate(lines):
        handle = line.strip()
        points = contestants.get(handle, 0)
        data.append({"Handle": handle, "Points": points})
    
    # Create DataFrame and save to temporary Excel file
    df = pd.DataFrame(data)
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(temp_file.name, index=False)
    temp_file.close()
    
    return temp_file.name

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        contest_id = request.form.get('contest_id')
        handles_text = request.form.get('handles')
        
        if not contest_id or not handles_text:
            flash('Please provide both contest ID and handles', 'error')
            return redirect(url_for('index'))
        
        # Validate contest ID is a number
        try:
            contest_id = int(contest_id)
        except ValueError:
            flash('Contest ID must be a valid number', 'error')
            return redirect(url_for('index'))
        
        # Process the data and generate Excel file
        excel_file_path = process_contest_data(contest_id, handles_text)
        
        # Send the file to the user
        return send_file(
            excel_file_path, 
            as_attachment=True, 
            download_name=f'contest_{contest_id}_results.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'Error processing request: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # For development
    app.run(debug=True, host='0.0.0.0', port=5000)
