import subprocess
import json
import sys

def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            print(f"Error running command: {command}")
            print(result.stderr)
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"Exception running command {command}: {e}")
        return None

def main():
    print("--- Appwrite Function Diagnostic Tool ---")
    
    # 1. Check if Appwrite CLI is installed
    version = run_command("appwrite -v")
    if not version:
        print("FAIL: Appwrite CLI not found. Please install it with 'npm install -g appwrite-cli'")
        sys.exit(1)
    print(f"OK: Appwrite CLI version {version}")

    # 2. Check if logged in
    # Note: 'appwrite whoami' might not be available in all versions or might require interaction
    # Better to check if we can get project info
    
    # Load config to get IDs
    try:
        with open("appwrite.config.json", "r") as f:
            config = json.load(f)
            project_id = config.get("projectId")
            function_id = config.get("functions", [{}])[0].get("$id")
    except Exception as e:
        print(f"FAIL: Could not read appwrite.config.json: {e}")
        sys.exit(1)

    print(f"Project ID from config: {project_id}")
    print(f"Function ID from config: {function_id}")

    if not project_id or not function_id:
        print("FAIL: Missing project ID or function ID in config.")
        sys.exit(1)

    # 3. Fetch function details
    print(f"\nFetching details for function '{function_id}'...")
    details_str = run_command(f"appwrite functions get --function-id {function_id} --json")
    
    if not details_str:
        print("FAIL: Could not fetch function details. Are you logged in and using the correct project?")
        print("Try: appwrite login")
        sys.exit(1)

    try:
        details = json.loads(details_str)
        execute = details.get("execute", [])
        enabled = details.get("enabled", False)
        
        print(f"OK: Function found.")
        print(f"Enabled: {enabled}")
        print(f"Execute Permissions: {execute}")
        
        if "any" in execute or "role:all" in execute or ("users" in execute and "guests" in execute):
            print("OK: Public execution is enabled.")
        else:
            print("WARNING: Public execution might be disabled. 'any' role not found in execute permissions.")
            print("Fix: appwrite functions update --function-id {function_id} --execute any")

        # 4. Show Function Domain
        # Function domains are often in the 'domains' field or can be constructed
        # Constructing it for Appwrite Cloud:
        print(f"\nSuggested Function URL: https://{function_id}.{project_id}.appwrite.global")
        print("Check the 'Domains' tab in Appwrite Console for custom domains.")

    except Exception as e:
        print(f"FAIL: Could not parse function details: {e}")

if __name__ == "__main__":
    main()
