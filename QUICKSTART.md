# Quick Start Guide

Get the Battery Aggregator running in under 5 minutes!

## Prerequisites Check

Before starting, verify you have:
- [ ] Victron Cerbo GX (or compatible GX device) with SSH access
- [ ] Root password for your Cerbo
- [ ] Multiple battery BMS units connected and visible on D-Bus
- [ ] Basic familiarity with SSH and command line

## Step 1: Clone Repository (30 seconds)

```bash
git clone https://github.com/drurew/Battery-Aggregator.git
cd Battery-Aggregator
```

## Step 2: Copy to Cerbo (30 seconds)

Replace `<CERBO_IP>` with your Cerbo's IP address (find it in Settings → Ethernet):

```bash
scp bms_aggregator.py install_aggregator.sh root@<CERBO_IP>:/tmp/
```

**Example:**
```bash
scp bms_aggregator.py install_aggregator.sh root@192.168.1.100:/tmp/
```

## Step 3: Install on Cerbo (2 minutes)

SSH into your Cerbo and run the installer:

```bash
ssh root@<CERBO_IP>
cd /tmp
chmod +x install_aggregator.sh
./install_aggregator.sh
```

**Watch for:**
- ✅ "Installation complete!"
- ✅ "Service is running!"

## Step 4: Activate Aggregator (30 seconds)

Set as the active battery service:

```bash
dbus -y com.victronenergy.settings /Settings/SystemSetup/BatteryService SetValue 'com.victronenergy.battery/280'
```

## Step 5: Verify (1 minute)

Check it's working:

```bash
# Should show aggregated SOC
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Soc GetValue

# Should show 'com.victronenergy.battery/280'
dbus -y com.victronenergy.system /ActiveBatteryService GetValue
```

**Expected output:**
```
83.0
'com.victronenergy.battery/280'
```

## Done! 

Your batteries are now aggregated. Monitor the system:

```bash
# Live log view
tail -f /var/log/bms-aggregator/current

# Check imbalance status (0=OK, 1=Warning, 2=Alarm)
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Alarms/CellImbalance GetValue
```

## Troubleshooting

### "Service not starting"
```bash
# Check logs for errors
tail -50 /var/log/bms-aggregator/current
```

### "BMS services not found"
Edit the configuration to match your BMS:
```bash
vi /data/bms_aggregator/bms_aggregator.py
# Change lines 31-35 to your BMS service names
svc -t /service/bms-aggregator
```

### "Not appearing in battery list"
Wait 10 seconds, then:
```bash
svc -t /service/dbus-systemcalc-py
sleep 5
dbus -y com.victronenergy.system /AvailableBatteryServices GetValue
```



