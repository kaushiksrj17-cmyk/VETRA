import asyncio
import json

import websockets


WEBSOCKET_URL = "ws://127.0.0.1:8000/ws/monitoring"


async def receive_messages(websocket):

    while True:

        message = await websocket.recv()

        data = json.loads(message)

        print("\n" + "=" * 60)

        if data.get("type") == "health_reading":

            reading = data.get("data", {})

            print("📡 LIVE VETRA HEALTH READING")

            print("=" * 60)

            print(
                f"Animal       : "
                f"{reading.get('animal_id')}"
            )

            print(
                f"Device       : "
                f"{reading.get('device_id')}"
            )

            print(
                f"Temperature  : "
                f"{reading.get('temperature_c')} °C"
            )

            print(
                f"Heart Rate   : "
                f"{reading.get('heart_rate_bpm')} BPM"
            )

            print(
                f"Activity     : "
                f"{reading.get('activity_level')}%"
            )

            print(
                f"Rumination   : "
                f"{reading.get('rumination_level')}%"
            )

            print(
                f"Respiratory  : "
                f"{reading.get('respiratory_rate')} /min"
            )

            print(
                f"Source       : "
                f"{reading.get('source')}"
            )

            print(
                f"Recorded     : "
                f"{reading.get('recorded_at')}"
            )

            print("=" * 60)

        else:

            print("Received:")
            print(
                json.dumps(
                    data,
                    indent=2
                )
            )


async def test_websocket():

    print("=" * 60)
    print("VETRA REAL-TIME MONITORING TEST")
    print("=" * 60)

    print(
        f"\nConnecting to:\n"
        f"{WEBSOCKET_URL}"
    )

    try:

        async with websockets.connect(
            WEBSOCKET_URL
        ) as websocket:

            print(
                "\n[SUCCESS] 🟢 WebSocket connected!"
            )

            print(
                "\nSending ping..."
            )

            await websocket.send("ping")

            response = await websocket.recv()

            print(
                "\nInitial response:"
            )

            print(
                json.dumps(
                    json.loads(response),
                    indent=2
                )
            )

            print(
                "\n[LISTENING] 📡 Waiting for "
                "live health readings..."
            )

            print(
                "Start the IoT simulator if it "
                "is not already running."
            )

            await receive_messages(
                websocket
            )

    except Exception as error:

        print(
            "\n[ERROR] WebSocket connection failed."
        )

        print(error)


if __name__ == "__main__":

    try:

        asyncio.run(
            test_websocket()
        )

    except KeyboardInterrupt:

        print(
            "\n\nWebSocket test stopped."
        )