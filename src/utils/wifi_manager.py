from unittest.mock import MagicMock
import subprocess
import time
from typing import List, Dict, Tuple, Any
import re
import logging
import os

# Setup logger
logger = logging.getLogger(__name__)

class WiFiManager:
    @classmethod
    def scan_networks(cls):
        """Scan for available WiFi networks"""
        logger.info("Scanning for WiFi networks...")
        try:
            # Force a rescan
            subprocess.run(['sudo', 'nmcli', 'device', 'wifi', 'rescan'], 
                         capture_output=True, text=True)
            
            # Get all networks with tabular format
            result = subprocess.run(
                ['sudo', 'nmcli', '-t', '-f', 'IN-USE,SIGNAL,SSID,SECURITY', 'device', 'wifi', 'list'], 
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                logger.error(f"nmcli failed: {result.stderr}")
                return []
            
            networks = []
            seen_ssids = set()
            
            for line in result.stdout.strip().split('\n'):
                try:
                    if not line:
                        continue
                    
                    parts = line.split(':')
                    if len(parts) >= 3:
                        in_use = parts[0] == '*'
                        signal = int(parts[1])
                        ssid = parts[2]
                        security = parts[3] if len(parts) > 3 and parts[3] != '--' else 'none'
                        
                        if ssid and ssid not in seen_ssids:
                            seen_ssids.add(ssid)
                            networks.append({
                                'ssid': ssid,
                                'signal': signal,
                                'security': security,
                                'active': in_use
                            })
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing line '{line}': {str(e)}")
                    continue
            
            networks.sort(key=lambda x: x['signal'], reverse=True)
            logger.info(f"Found {len(networks)} unique networks: {networks}")
            return networks
            
        except Exception as e:
            logger.error(f"Error scanning networks: {str(e)}", exc_info=True)
            return []

    @classmethod
    def _parse_network_list(cls, output):
        """Helper method to parse network list output"""
        networks = []
        seen_ssids = set()
        for line in output.strip().split('\n'):
            if ':' in line:
                parts = line.split(':')
                if len(parts) >= 3 and parts[1] and parts[1] not in seen_ssids:
                    ssid = parts[1]
                    seen_ssids.add(ssid)
                    networks.append({
                        'ssid': ssid,
                        'signal': int(parts[0]),
                        'security': parts[2] if parts[2] else 'none',
                        'active': len(parts) > 3 and parts[3] == 'yes'
                    })
        networks.sort(key=lambda x: x['signal'], reverse=True)
        return networks

    @staticmethod
    def get_saved_connections() -> List[str]:
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show'],
                capture_output=True,
                text=True,
                check=True
            )
            saved = []
            for line in result.stdout.strip().split('\n'):
                if ':802-11-wireless' in line:  # Only get WiFi connections
                    saved.append(line.split(':')[0])
            return saved
        except Exception as e:
            print(f"Error getting saved connections: {str(e)}")
            return []

    @classmethod
    def connect_to_network(cls, ssid, password=None):
        """Connect to a WiFi network using nmcli"""
        logger.info(f"Connecting to network: {ssid}")
        try:
            if password:
                cmd = ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password]
            else:
                cmd = ['nmcli', 'device', 'wifi', 'connect', ssid]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                'success': result.returncode == 0,
                'message': result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
            }
        except subprocess.TimeoutExpired as e:
            logger.error(f"Connection timeout: {str(e)}")
            return {'success': False, 'message': 'Connection timeout'}
        except Exception as e:
            logger.error(f"Error connecting to network: {str(e)}", exc_info=True)
            return {'success': False, 'message': str(e)}

    @classmethod
    def disconnect(cls):
        """Disconnect from current WiFi network using nmcli"""
        logger.info("Disconnecting from WiFi")
        try:
            result = subprocess.run(['nmcli', 'device', 'disconnect', 'wlan0'], 
                                 capture_output=True, text=True)
            return {
                'success': result.returncode == 0,
                'message': result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
            }
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}", exc_info=True)
            return {'success': False, 'message': str(e)}

    @classmethod
    def get_current_connection(cls):
        """Get current WiFi connection details"""
        logger.info("Getting current WiFi connection...")
        try:
            result = subprocess.run(['nmcli', '-t', '-f', 'ACTIVE,SIGNAL,SSID', 'device', 'wifi'], 
                                 capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        active, signal, ssid = line.split(':')
                        if active == 'yes':
                            return {
                                'ssid': ssid,
                                'signal': int(signal),
                                'connected': True
                            }
            return None
        except Exception as e:
            logger.error(f"Error getting current connection: {str(e)}", exc_info=True)
            return None