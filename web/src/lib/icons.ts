export const Icons = {
  // ... copy existing Icons object
};

export function getWifiIcon(signal_strength: number): string {
  if (signal_strength >= 80) return Icons.wifiStrong;
  if (signal_strength >= 60) return Icons.wifiGood;
  if (signal_strength >= 40) return Icons.wifiFair;
  return Icons.wifiWeak;
} 