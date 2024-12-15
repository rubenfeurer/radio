export interface RadioStation {
  name: string;
  url: string;
  slot: number;
  isPlaying: boolean;
}

export interface RadioStatus {
  volume: number;
  currentStation: number | null;
  stations: RadioStation[];
  isConnected: boolean;
}

export interface WSMessage {
  type: 'status_update' | 'station_control' | 'volume_control';
  data: any;
}
