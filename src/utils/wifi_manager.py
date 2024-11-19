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
            # Get saved networks first
            saved_networks = cls.get_saved_connections()
            logger.info(f"Found saved networks: {saved_networks}")
            
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
                            is_saved = ssid in saved_networks
                            logger.info(f"Network {ssid}: active={in_use}, saved={is_saved}")
                            networks.append({
                                'ssid': ssid,
                                'signal': signal,
                                'security': security,
                                'active': in_use,
                                'saved': is_saved
                            })
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing line '{line}': {str(e)}")
                    continue
            
            networks.sort(key=lambda x: x['signal'], reverse=True)
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

    @classmethod
    def get_saved_connections(cls) -> List[str]:
        """Get list of saved WiFi connections"""
        try:
            # Get all connections
            result = subprocess.run(
                ['sudo', 'nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show'],
                capture_output=True,
                text=True,
                check=True
            )
            
            saved = []
            for line in result.stdout.strip().split('\n'):
                if ':802-11-wireless' in line:  # Only get WiFi connections
                    name = line.split(':')[0]
                    if name != 'preconfigured':  # Skip the preconfigured connection
                        saved.append(name)
                    else:
                        # If it's preconfigured, get its SSID
                        ssid_result = subprocess.run(
                            ['sudo', 'nmcli', '-g', '802-11-wireless.ssid', 'connection', 'show', 'preconfigured'],
                            capture_output=True,
                            text=True
                        )
                        if ssid_result.returncode == 0 and ssid_result.stdout.strip():
                            saved.append(ssid_result.stdout.strip())
            
            logger.info(f"Found saved connections: {saved}")
            return saved
        except Exception as e:
            logger.error(f"Error getting saved connections: {str(e)}")
            return []

    @classmethod
    def connect_to_network(cls, ssid: str, password: str) -> Dict[str, Any]:
        """Connect to a WiFi network using nmcli."""
        try:
            logger.info(f"Attempting to connect to network: {ssid}")
            
            # Check if already connected to this network
            current = cls.get_current_connection()
            if current and current.get('ssid') == ssid:
                logger.info(f"Already connected to {ssid}")
                return {'success': True, 'message': f'Already connected to {ssid}'}

            # Escape special characters in SSID and password
            escaped_ssid = ssid.replace('"', '\\"')
            escaped_password = password.replace('"', '\\"')

            # Construct the nmcli command
            command = [
                'sudo', 'nmcli', 'device', 'wifi', 'connect', escaped_ssid,
                'password', escaped_password
            ]
            
            logger.info(f"Executing connection command for {ssid}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True
            )
            
            logger.info(f"Connection command output: {result.stdout}")
            if result.stderr:
                logger.error(f"Connection error: {result.stderr}")

            if result.returncode == 0:
                logger.info(f"Successfully connected to {ssid}")
                return {'success': True, 'message': f'Successfully connected to {ssid}'}
            else:
                error_msg = result.stderr or result.stdout or 'Unknown error'
                logger.error(f"Failed to connect to {ssid}: {error_msg}")
                return {'success': False, 'message': error_msg}

        except subprocess.TimeoutExpired as e:
            error_msg = f"Connection timed out while connecting to {ssid}"
            logger.error(f"{error_msg}: {str(e)}")
            return {'success': False, 'message': error_msg}
        except Exception as e:
            error_msg = f"Error connecting to {ssid}: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}

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