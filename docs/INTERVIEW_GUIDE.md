# GridMind — Interview Guide & Technical Defense

## 1. Pitches
- **30-Second Pitch**: "GridMind is a physics-informed energy digital twin and optimization platform. It models microgrid power flow, schedules battery storage to minimize time-of-use costs and peak demand penalties, and detects sensor anomalies in real-time with zero-hallucination AI operational analytics."
- **2-Minute Pitch**: "Industrial microgrids face volatile energy tariffs and intermittent renewable generation. GridMind models physical grid assets—solar arrays, battery storage systems, critical loads, and grid interconnects—as a digital twin. Our backend uses linear programming to schedule optimal battery charging during low-tariff solar peaks and discharging during expensive peak demand windows. We continuously run rolling-window statistical anomaly detection to catch sensor drift and voltage sags. An AI energy analyst interprets telemetry logs and suggests efficiency measures, guarded by deterministic physics constraints that prevent unsafe control signals."

## 2. Key Technical Q&A
- **Q: How do you handle battery degradation in your dispatch optimization?**
  - **A**: We introduce a degradation cost penalty per kWh cycled into the objective function. This prevents micro-cycling during negligible price differentials, ensuring the battery only discharges when tariff spreads exceed the marginal cost of battery cell wear.
- **Q: What happens if solar generation drops unexpectedly?**
  - **A**: The digital twin executes an event-driven fast re-dispatch loop: battery discharge ramps up within inverter slew rate limits to absorb the load step, preventing a costly grid peak demand spike.
