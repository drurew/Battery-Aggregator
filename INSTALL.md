# Installation Guide

Complete step-by-step installation instructions for the Battery Aggregator service on Victron Venus OS.

## Prerequisites

### Required Information

Before starting, gather:
1. **Cerbo GX IP address** (e.g., `192.168.1.100`)
2. **Root password** for SSH access
3. **BMS service names** on your system

### Find Your BMS Service Names

SSH into your Cerbo and run:
```bash
dbus -y com.victronenergy.system /AvailableBatteryServices GetValue
```

Look for entries like:
- `com.victronenergy.battery.canopen_bms_node1`
- `com.victronenergy.battery.socketcan_can0_di512_uc6147`
- `com.victronenergy.battery.ttyUSB0`

## Installation Methods

### Method 1: Quick Install (Recommended)

**From your computer:**

1. **Download files**:
   ```bash
   git clone https://github.com/drurew/Battery-Aggregator.git
   cd Battery-Aggregator
   ```

2. **Copy to Cerbo**:
   ```bash
   scp bms_aggregator.py install_aggregator.sh root@<CERBO_IP>:/tmp/
   ```

3. **SSH into Cerbo and install**:
   ```bash
   ssh root@<CERBO_IP>
   cd /tmp
   chmod +x install_aggregator.sh
   ./install_aggregator.sh
   ```

4. **Configure battery service** (wait 10 seconds for system to detect):
   ```bash
   dbus -y com.victronenergy.settings /Settings/SystemSetup/BatteryService SetValue 'com.victronenergy.battery/280'
   ```

5. **Verify**:
   ```bash
   dbus -y com.victronenergy.system /ActiveBatteryService GetValue
   dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Soc GetValue
   ```

### Method 2: Manual Installation

**On the Cerbo GX (via SSH):**

1. **Create directories**:
   ```bash
   mkdir -p /data/bms_aggregator
   mkdir -p /var/log/bms-aggregator
   ```

2. **Copy Python script**:
   ```bash
   # Upload bms_aggregator.py to /data/bms_aggregator/
   chmod +x /data/bms_aggregator/bms_aggregator.py
   ```

3. **Create service directory**:
   ```bash
   mkdir -p /service/bms-aggregator/log
   ```

4. **Create run script**:
   ```bash
   cat > /service/bms-aggregator/run <<'EOF'
   #!/bin/sh
   exec 2>&1
   exec /usr/bin/python3 /data/bms_aggregator/bms_aggregator.py
   EOF
   chmod +x /service/bms-aggregator/run
   ```

5. **Create log run script**:
   ```bash
   cat > /service/bms-aggregator/log/run <<'EOF'
   #!/bin/sh
   exec multilog t /var/log/bms-aggregator
   EOF
   chmod +x /service/bms-aggregator/log/run
   ```

6. **Service will start automatically** within 5-10 seconds (daemontools)

## Configuration

### Customize for Your System

Edit `/data/bms_aggregator/bms_aggregator.py`:

**1. Change BMS service names** (lines 31-35):
```python
self.bms_services = [
    'com.victronenergy.battery.YOUR_BMS_1',
    'com.victronenergy.battery.YOUR_BMS_2',
    'com.victronenergy.battery.YOUR_BMS_3'
]
```

**2. Adjust device instance** if 280 is taken (line 28):
```python
self.device_instance = 280  # Change if conflicts
```

**3. Modify charge current limits** (lines 68-69):
```python
self.nominal_charge_current = 150.0  # Your max current
self.reduced_charge_current = 50.0   # Reduced for imbalance
```

**4. Set total capacity** (line 51):
```python
self.dbusservice.add_path('/Capacity', 450.0, writeable=False)  # 3x 150Ah
```

**5. Adjust max charge voltage** (line 67):
```python
self.dbusservice.add_path('/Info/MaxChargeVoltage', 14.2, writeable=False)
```

After changes, restart the service:
```bash
svc -t /service/bms-aggregator
```

### Configure DVCC (Distributed Voltage and Current Control)

**Via Cerbo touch screen:**
1. Settings → DVCC
2. Enable: **On**
3. Limit charge current: **Set to aggregator max** (e.g., 150A)
4. SVS (Shared Voltage Sense): **On**
5. SCS (Shared Current Sense): **On**
6. STS (Shared Temperature Sense): **On**

**Via VRM Portal:**
1. Settings → System Setup → DVCC
2. Enable the same settings

### Set as Active Battery Service

**Method A: Via D-Bus (immediate)**
```bash
dbus -y com.victronenergy.settings /Settings/SystemSetup/BatteryService SetValue 'com.victronenergy.battery/280'
```

**Method B: Via VRM Portal**
1. Settings → System Setup → Battery Monitor
2. Select "BMS Aggregator" or the aggregator service name

**Method C: Via Cerbo Screen**
1. Settings → System Setup → Battery Monitor
2. Choose aggregator from list

## Verification

### Check Service is Running
```bash
svstat /service/bms-aggregator
```
Expected output: `/service/bms-aggregator: up (pid XXXXX) XXX seconds`

### Check Logs for Errors
```bash
tail -30 /var/log/bms-aggregator/current
```
Look for:
- `BMS Aggregator Service Starting`
- `registered ourselves on D-Bus`
- `Entering main loop`
- Regular SOC updates

### Verify D-Bus Registration
```bash
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /ProductName GetValue
```
Expected: `'BMS Aggregator'`

### Check Aggregated Values
```bash
# SOC (should be lowest of your batteries)
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Soc GetValue

# Voltage (should be average)
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Dc/0/Voltage GetValue

# Current charge limit
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Info/MaxChargeCurrent GetValue

# Imbalance status (0=OK, 1=Warning, 2=Alarm)
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Alarms/CellImbalance GetValue
```

### Verify System is Using Aggregator
```bash
# Should show aggregator service
dbus -y com.victronenergy.system /ActiveBatteryService GetValue

# Should match aggregator SOC
dbus -y com.victronenergy.system /Dc/Battery/Soc GetValue
```

### Check MultiPlus/Quattro Receives Data

**If using ESS mode:**
```bash
# Should match aggregator SOC
dbus -y com.victronenergy.vebus.ttyS4 /Soc GetValue

# Should match aggregator voltage
dbus -y com.victronenergy.vebus.ttyS4 /BatterySense/Voltage GetValue
```

## Post-Installation

### Monitor Battery Behavior

For the first 24 hours, monitor:
1. **SOC convergence** - Batteries should slowly equalize
2. **Charge current changes** - Watch for automatic reductions during imbalance
3. **Alarm status** - Ensure no false alarms
4. **Individual battery SOCs** - Track progress toward balance

### VRM Portal Dashboard

Check your VRM portal (https://vrm.victronenergy.com) for:
- Battery SOC graph
- Charge current graph
- Any alarms triggered

### Expected Behavior During Imbalance

**11% SOC difference** (e.g., 93% vs 82%):
- Alarm: Warning (1) - Yellow alert
- Charge current: Reduced to 66% (e.g., 150A → 99A)
- Logs: "Battery imbalance warning: 11% difference"

**As batteries equalize**:
- SOC difference decreases
- Charge current automatically increases
- Alarm clears when <5% difference

## Troubleshooting Install Issues

### Service Won't Start

**Check Python path**:
```bash
which python3
```
Update run script if needed.

**Check velib_python**:
```bash
ls /opt/victronenergy/dbus-systemcalc-py/ext/velib_python/
```
Should contain `vedbus.py`

**Check permissions**:
```bash
ls -la /data/bms_aggregator/
```
Script should be executable (`-rwxr-xr-x`)

### Can't Find BMS Services

**List all battery services**:
```bash
dbus | grep battery
```

**Check if BMS is online**:
```bash
dbus -y com.victronenergy.battery.canopen_bms_node1 /Connected GetValue
```
Should return `1`

### Aggregator Not Selectable

**Wait for detection** - systemcalc scans every ~10 seconds

**Restart systemcalc**:
```bash
svc -t /service/dbus-systemcalc-py
sleep 5
dbus -y com.victronenergy.system /AvailableBatteryServices GetValue
```

**Check device instance**:
```bash
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /DeviceInstance GetValue
```
If it conflicts, change in script.

### Values Not Updating

**Check update frequency** in logs:
```bash
tail -f /var/log/bms-aggregator/current | grep SOC
```
Should update every 2 seconds.

**Verify BMS data is live**:
```bash
watch -n 1 'dbus -y com.victronenergy.battery.canopen_bms_node1 /Soc GetValue'
```

## Backup and Recovery

### Backup Configuration
```bash
# On Cerbo
cp /data/bms_aggregator/bms_aggregator.py /data/bms_aggregator/bms_aggregator.py.backup
```

### Restore Previous Battery Service
```bash
# Set back to default
dbus -y com.victronenergy.settings /Settings/SystemSetup/BatteryService SetValue 'default'

# Or specific service
dbus -y com.victronenergy.settings /Settings/SystemSetup/BatteryService SetValue 'com.victronenergy.battery/1'
```

### Persistent Configuration

Venus OS uses `/data` for persistent storage. Files in `/service` may be reset on firmware updates. To persist across updates:

1. Keep master copy in `/data/bms_aggregator/`
2. Create startup script: `/data/rc.local`
   ```bash
   #!/bin/bash
   # Restore aggregator service
   if [ ! -d /service/bms-aggregator ]; then
       /data/bms_aggregator/install_aggregator.sh
   fi
   ```

## Next Steps

- Review [README.md](README.md) for features and monitoring
- Check logs regularly: `tail -f /var/log/bms-aggregator/current`
- Monitor VRM Portal for system behavior
- Join [Victron Community](https://community.victronenergy.com/) for support

## Getting Help

If issues persist:

1. **Collect diagnostic info**:
   ```bash
   svstat /service/bms-aggregator
   tail -100 /var/log/bms-aggregator/current
   dbus -y com.victronenergy.system /AvailableBatteryServices GetValue
   dbus | grep battery | head -20
   ```

2. **Post on GitHub Issues** with:
   - Venus OS version
   - Battery/BMS models
   - Service status and logs
   - Error messages

3. **Victron Community Forum**:
   - Search existing threads
   - Post in "Modifications" section
   - Include system details
