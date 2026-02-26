import os
import subprocess
text = "test"
command = ['claude', '-p', '-c', text, '--output-format', 'json']
            
env = os.environ.copy()
env['TERM'] = 'dumb'
env['PYTHONIOENCODING'] = 'utf-8'

result = subprocess.run(
    command,
    capture_output=True,
    text=True,
    timeout=600,  # Increased timeout to 60 seconds for long-running commands
    env=env
)

print(result)