class Config:
    @staticmethod
    def load_config():
        # Your config loading logic here
        return {
            'default_stations': [
                "GDS.FM",
                "Ambi Nature Radio",
                "SRF 3"
            ],
            'default_volume': 80,
            'gpio': {
                'rotary': {
                    'clk': 11,
                    'dt': 9,
                    'sw': 10
                },
                'settings': {
                    'debounce_time': 300,
                    'pull_up': True
                }
            },
            'streams': [
                {
                    'name': "GDS.FM",
                    'url': "http://stream.gds.fm:8000/stream"
                },
                {
                    'name': "Ambi Nature Radio",
                    'url': "http://radio.ambi.nature/stream"
                },
                {
                    'name': "SRF 3",
                    'url': "http://stream.srfradio.ch/srf3"
                }
            ]
        } 