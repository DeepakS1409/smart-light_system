# Known System Limitations

1. **Feeder-Level vs. Bulb-Level Detection**:
   - The IoT monitoring box monitors aggregate electrical flow at the feeder/group transformer level.
   - It **cannot** pinpoint which individual bulb has burned out along the line unless the entire branch experiences an open/short circuit.
   - Individual bulb failures are crowd-reported via citizen QR codes.

2. **Demonstration & Synthetic Data**:
   - All pole coordinates, feeder voltage/current values, and citizen complaints are synthetic test fixtures explicitly labelled as "Demonstration data".
   - No connection is made to physical power mains or utility switches.

3. **Localhost & Mobile QR Testing**:
   - Scanning a generated QR code with a phone will not resolve `localhost` or `127.0.0.1`.
   - For smartphone testing, the Flask server must be run on `0.0.0.0` and the QR codes generated with the host machine's Wi-Fi LAN IP (e.g., `http://192.168.1.X:5000/...`).

4. **Routing Optimization**:
   - The multi-stop technician dispatch route uses a greedy Nearest-Neighbour Euclidean approximation, not a live turn-by-turn traffic router.

5. **Incident Intelligence**:
   - Intelligence rules (priority assignment, duplicate detection, maintenance recommendations) are strictly deterministic and rule-based; no machine learning or black-box predictions are claimed.

6. **External Notifications (SMS / Telegram / Email)**:
   - External notification channels are optional and currently off by default to maintain zero external account/API dependencies. Deliveries are logged in the database audit history.
