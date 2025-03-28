import subprocess
import json
import xmltodict
from typing import Dict, List

def get_current_registrations(format: str = "json") -> List[Dict]:
    """Obtém os registros atuais do FreeSwitch no formato especificado"""
    try:
        command = f'fs_cli -x "show registrations as {format}"'
        result = subprocess.run(command, shell=True, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
        
        if format == "json":
            return json.loads(result.stdout)["rows"]
        elif format == "xml":
            data = xmltodict.parse(result.stdout)
            if isinstance(data["result"]["row"], list):
                return data["result"]["row"]
            return [data["result"]["row"]]
        else:
            # Formato padrão (CSV-like)
            lines = result.stdout.splitlines()
            headers = lines[0].split(',')
            registrations = []
            for line in lines[1:]:
                if line.strip():
                    values = line.split(',')
                    registrations.append(dict(zip(headers, values)))
            return registrations
    except subprocess.CalledProcessError as e:
        print(f"Error getting registrations: {e.stderr}")
        return []
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return []

def get_active_users_count() -> int:
    """Retorna a contagem de usuários ativos"""
    try:
        command = 'fs_cli -x "show registrations as xml" | grep reg_user | wc -l'
        result = subprocess.run(command, shell=True, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
        return int(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"Error getting active users count: {e.stderr}")
        return 0
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 0