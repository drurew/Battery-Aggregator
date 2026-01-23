# Example Configurations

This directory contains example configurations for various battery setups.

## Available Examples

### 1. [pylontech_3_batteries.py](pylontech_3_batteries.py)
Configuration for 3× Pylontech US2000C batteries (48V system)

### 2. [superb_2_batteries.py](superb_2_batteries.py)
Configuration for 2× SuperB Epsilon batteries (12V system)

### 3. [rec_bms_4_batteries.py](rec_bms_4_batteries.py)
Configuration for 4× REC BMS batteries (24V system)

## How to Use Examples

1. **Copy example to main directory**:
   ```bash
   cp examples/pylontech_3_batteries.py bms_aggregator.py
   ```

2. **Edit for your system**:
   - Change BMS service names to match your devices
   - Adjust capacity, voltage, and current limits
   - Modify imbalance thresholds if desired

3. **Deploy to Cerbo**:
   ```bash
   scp bms_aggregator.py root@<CERBO_IP>:/data/bms_aggregator/
   ```

4. **Restart service**:
   ```bash
   ssh root@<CERBO_IP> "svc -t /service/bms-aggregator"
   ```

## Creating Your Own Configuration

See [CONFIGURATION.md](../CONFIGURATION.md) for detailed guidance on customizing settings.

### Key Values to Change

1. **BMS Service Names** (lines 31-35): Match your actual D-Bus service names
2. **Device Instance** (line 28): Ensure it's unique (280-299 typically available)
3. **Total Capacity** (line 51): Sum of all battery capacities
4. **Charge Voltage** (line 67): Match your battery chemistry
5. **Charge Current** (lines 68-69): Match your battery specifications

## Testing Configurations

Always test on a non-critical system first:

1. Monitor logs: `tail -f /var/log/bms-aggregator/current`
2. Check values: `dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Soc GetValue`
3. Verify behavior during charge/discharge cycles
4. Monitor for 24+ hours to ensure stability

## Contributing Examples

Have a working configuration? Please share!

1. Fork the repository
2. Add your example to this directory
3. Include comments explaining your setup
4. Submit a pull request

Include in your example:
- Battery brand and model
- BMS type and communication protocol
- System voltage (12V/24V/48V)
- Total capacity
- Any special considerations
