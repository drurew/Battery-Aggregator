# Battery Aggregator for Victron Venus OS

A Python service that aggregates State of Charge (SOC) and voltage data from multiple battery BMS units connected to a Victron Cerbo GX / Venus OS system. Designed for parallel battery banks where you want unified battery monitoring and intelligent charge control.

## Features

- **Multi-Battery Aggregation**: Combines data from multiple BMS units (tested with 3x SuperB Epsilon V2 batteries)
- **Conservative SOC Selection**: Uses the lowest SOC reading for safety
- **Voltage Averaging**: Averages voltage readings across all batteries
- **Smart Imbalance Detection**: Monitors both cell-level (within battery) and battery-level (between batteries) imbalance
- **Dynamic Charge Limiting**: Automatically reduces charge current when imbalance is detected to protect batteries
- **Alarm Integration**: Monitors BMS internal cell alarms and propagates to system
- **Seamless VE.Bus Integration**: Works with MultiPlus/Quattro inverter/chargers via ESS

## How It Works

### Aggregation Strategy

The aggregator reads data from multiple BMS services on the D-Bus:
- **SOC**: Uses the **lowest** value for conservative charging decisions
- **Voltage**: Uses the **average** across all batteries
- **Current**: Sums currents (parallel configuration)
- **Temperature**: Averages temperature readings

### Imbalance Protection

Automatically adjusts charging based on battery state differences:

| SOC Difference | Alarm Level | Max Charge Current | Action |
|---------------|-------------|-------------------|---------|
| 0-5% | OK (0) | 100% (150A) | Normal operation |
| 5-15% | OK (0) | 85% (128A) | Slight reduction |
| 15-20% | Warning (1) | 66% (99A) | Moderate reduction |
| >20% | Alarm (2) | 33% (50A) | Severe reduction |
| BMS Cell Alarm | Alarm (2) | 33% (50A) | BMS detected internal issue |

As batteries equalize, charge current automatically increases back to normal.

## Configuration

Starting with v1.1.0, the aggregator supports a configuration file for easy customization. Copy `config.ini` to `/data/bms_aggregator/` on your Cerbo GX and edit the values:

```bash
scp config.ini root@<cerbo-ip>:/data/bms_aggregator/
ssh root@<cerbo-ip>
nano /data/bms_aggregator/config.ini
# Edit thresholds as needed
svc -t /service/bms-aggregator  # Restart service
```

### Configuration Options

The config file allows you to adjust:
- **Imbalance thresholds**: When to trigger warnings and alarms
- **Charge current limits**: How much to reduce charging during imbalance
- **Battery parameters**: Capacity, voltages, discharge limits
- **BMS service names**: Adapt to your specific setup
- **Update interval**: Balance responsiveness vs CPU usage
- **Debug logging**: Enable detailed logs for troubleshooting

See [CONFIGURATION.md](CONFIGURATION.md) for detailed documentation of all available options.

**Default Thresholds (v1.1.0)**:
- Warning: 15% SOC difference (increased from 10% in v1.1.0)
- Alarm: 20% SOC difference (increased from 15% in v1.1.0)

These defaults are suitable for battery banks where batteries have different charge/discharge characteristics and won't equalize naturally.

## Requirements

- Victron Cerbo GX or Venus OS device
- Multiple battery BMS units connected via CANopen or similar
- Venus OS v2.80 or later (tested on v2.217)
- SSH access to Cerbo GX
- MultiPlus/Quattro with firmware v556+ for full ESS support

## Installation

### Quick Install

1. **Copy files to Cerbo GX**:
   ```bash
   scp bms_aggregator.py root@<cerbo-ip>:/tmp/
   scp install_aggregator.sh root@<cerbo-ip>:/tmp/
   ```

2. **SSH into Cerbo and run installer**:
   ```bash
   ssh root@<cerbo-ip>
   cd /tmp
   chmod +x install_aggregator.sh
   ./install_aggregator.sh
   ```

3. **Set as active battery service**:
   ```bash
   dbus -y com.victronenergy.settings /Settings/SystemSetup/BatteryService SetValue 'com.victronenergy.battery/280'
   ```

### Manual Installation

See [INSTALL.md](INSTALL.md) for detailed step-by-step instructions.

## Configuration

### Customize BMS Services

Edit `bms_aggregator.py` to match your BMS service names:

```python
self.bms_services = [
    'com.victronenergy.battery.canopen_bms_node1',  # Change to your service names
    'com.victronenergy.battery.canopen_bms_node2',
    'com.victronenergy.battery.canopen_bms_node3'
]
```

Find your service names:
```bash
dbus -y com.victronenergy.system /AvailableBatteryServices GetValue
```

### Adjust Charge Current Limits

Modify these values in `bms_aggregator.py`:

```python
self.nominal_charge_current = 150.0  # Normal: 3x 50A
self.reduced_charge_current = 50.0   # Imbalanced: 1x 50A
```

### Customize Imbalance Thresholds

See the `update()` method for SOC difference thresholds (5%, 10%, 15%).

## Monitoring

### Check Service Status
```bash
svstat /service/bms-aggregator
```

### View Logs
```bash
tail -f /var/log/bms-aggregator/current
```

### Check Aggregated Values
```bash
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Soc GetValue
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Dc/0/Voltage GetValue
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Info/MaxChargeCurrent GetValue
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Alarms/CellImbalance GetValue
```

### Service Control
```bash
svc -d /service/bms-aggregator   # Stop
svc -u /service/bms-aggregator   # Start
svc -t /service/bms-aggregator   # Restart
```

## Troubleshooting

### Service Not Starting

Check logs for errors:
```bash
tail -50 /var/log/bms-aggregator/current
```

Verify BMS services are available:
```bash
dbus -y com.victronenergy.battery.canopen_bms_node1 /Soc GetValue
```

### Aggregator Not Appearing in Available Services

The aggregator uses device instance 280. If this conflicts, edit `bms_aggregator.py`:
```python
self.device_instance = 280  # Change to available instance
```

Check used instances:
```bash
dbus -y com.victronenergy.system /AvailableBatteryServices GetValue
```

### Imbalance Alarm Won't Clear

This is by design - batteries need to equalize. Monitor SOC differences:
```bash
dbus -y com.victronenergy.battery.canopen_bms_node1 /Soc GetValue
dbus -y com.victronenergy.battery.canopen_bms_node2 /Soc GetValue
dbus -y com.victronenergy.battery.canopen_bms_node3 /Soc GetValue
```

## Uninstallation

```bash
# Stop service
svc -d /service/bms-aggregator

# Remove service directory
rm -rf /service/bms-aggregator

# Remove data directory
rm -rf /data/bms_aggregator

# Remove logs
rm -rf /var/log/bms-aggregator

# Set battery service back to default
dbus -y com.victronenergy.settings /Settings/SystemSetup/BatteryService SetValue 'default'
```

## Technical Details

### D-Bus Paths Published

The aggregator registers as a battery service and provides:

**Standard Battery Paths:**
- `/Soc` - State of charge (%)
- `/Dc/0/Voltage` - Battery voltage (V)
- `/Dc/0/Current` - Battery current (A)
- `/Dc/0/Power` - Power (W)
- `/Dc/0/Temperature` - Temperature (°C)
- `/Capacity` - Total capacity (Ah)
- `/ConsumedAmphours` - Consumed energy (Ah)
- `/TimeToGo` - Estimated time remaining (s)

**Charge Limits:**
- `/Info/MaxChargeVoltage` - Maximum charge voltage (V)
- `/Info/MaxChargeCurrent` - Maximum charge current (A) - **Dynamic**
- `/Info/MaxDischargeCurrent` - Maximum discharge current (A)
- `/Info/BatteryLowVoltage` - Low voltage cutoff (V)

**Alarms:**
- `/Alarms/CellImbalance` - Imbalance detected (0=OK, 1=Warning, 2=Alarm)
- `/Alarms/LowVoltage` - Battery voltage too low
- `/Alarms/HighVoltage` - Battery voltage too high
- `/Alarms/LowSoc` - SOC too low
- Plus additional standard battery alarms

### Service Architecture

- **Service Name**: `com.victronenergy.battery.socketcan_can0_di280_uc1537`
- **Device Instance**: 280
- **Update Interval**: 2 seconds
- **Startup**: Automatic via daemontools
- **Dependencies**: VE.Bus service, BMS services, systemcalc

## Compatibility

### Tested With
- **Hardware**: Victron Cerbo GX
- **Venus OS**: v2.217
- **Batteries**: 3× SuperB Epsilon V2 150Ah (12V)
- **BMS Protocol**: CANopen
- **Inverter**: MultiPlus Compact 12/1200/50-16 (firmware v556)

### Should Work With
- Any Victron GX device (Cerbo GX, Ekrano GX, etc.)
- Venus OS v2.80+
- Any battery BMS that publishes standard Victron battery paths
- Any MultiPlus/Quattro with ESS support

## Contributing

Contributions welcome! Please:
1. Test thoroughly on your system
2. Document any configuration changes needed
3. Include example D-Bus paths for your BMS
4. Update compatibility list

## License

GPL3

## Disclaimer

This software modifies critical battery management functions. Use at your own risk. Always:
- Test in a safe environment first
- Monitor battery behavior closely after installation
- Have proper battery protection (fuses, disconnects)
- Understand your battery specifications
- Keep firmware and software updated

Incorrect battery management can lead to battery damage, fire, or injury.
