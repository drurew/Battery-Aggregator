#!/bin/bash

# Setup script for Battery Aggregator
# Supports Install and Uninstall

# Default to install if no argument provided
ACTION="install"
if [ $# -gt 0 ]; then
    ACTION=$1
fi

packageName="battery-aggregator"
installPath="/data/$packageName"
serviceName="bms-aggregator"
servicePath="/service/$serviceName"
logDir="/var/log/$serviceName"

# --- Helper Functions ---
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Venus OS Mod Registration Standard
register_mod() {
    local MOD_ID=$1
    local MOD_NAME=$2
    local MOD_VERSION=$3
    local MOD_REPO=$4
    local MOD_PATH=$5

    python3 -c "
import json
import os
import hashlib
import datetime

def get_hash(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

mod_id = '$MOD_ID'
data = {
    'id': '$MOD_ID',
    'name': '$MOD_NAME',
    'version': '$MOD_VERSION',
    'repository': '$MOD_REPO',
    'installed_at': datetime.datetime.utcnow().isoformat() + 'Z',
    'files': {}
}

root = '$MOD_PATH'
if os.path.isfile(root):
    data['files'][os.path.basename(root)] = get_hash(root)
else:
    for dirpath, dirnames, files in os.walk(root):
        if '__pycache__' in dirnames: dirnames.remove('__pycache__')
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        
        for f in files:
            if f.startswith('.'): continue
            if f.endswith(('.pyc', '.log', '.txt', '.md')): continue
            # Allow configuration modification (Tamper Evident Seal)
            if f.endswith(('.ini', '.yaml', '.json', '.conf', '.xml')): continue
            
            full_path = os.path.join(dirpath, f)
            rel_path = os.path.relpath(full_path, root)
            try:
                data['files'][rel_path] = get_hash(full_path)
            except: pass

manifest_dir = '/data/etc/venus-mods'
if not os.path.exists(manifest_dir):
    os.makedirs(manifest_dir)

with open(f'{manifest_dir}/{mod_id}.json', 'w') as f:
    json.dump(data, f, indent=2)
"
    log_message "Module '${MOD_ID}' registered to manifest."
}

install_package() {
    log_message "Installing $packageName..."

    # 1. Create installation directory
    if [ ! -d "$installPath" ]; then
        log_message "Creating directory $installPath"
        mkdir -p "$installPath"
    fi

    # 2. Copy files
    log_message "Copying files to $installPath"
    cp -r * "$installPath"
    
    # 3. Set permissions
    chmod +x "$installPath/bms_aggregator.py"
    
    # 4. Install Service
    install_service
    
    register_mod "bms-aggregator" "Battery Aggregator" "v1.0.0" "https://github.com/drurew/Battery-Aggregator" "$installPath"

    log_message "Installation complete."
}

install_service() {
    log_message "Installing service $serviceName..."
    
    # Create service directory
    mkdir -p "$servicePath"
    
    # Create run script
    cat > "$servicePath/run" <<EOF
#!/bin/sh
exec 2>&1
exec /usr/bin/python3 $installPath/bms_aggregator.py
EOF
    chmod +x "$servicePath/run"
    
    # Create log directory and run script
    mkdir -p "$servicePath/log"
    mkdir -p "$logDir"
    
    cat > "$servicePath/log/run" <<EOF
#!/bin/sh
exec multilog t $logDir
EOF
    chmod +x "$servicePath/log/run"
    
    # Allow daemontools to start the service
    log_message "Service configured. Daemontools should start it automatically."
}

uninstall_package() {
    log_message "Uninstalling $packageName..."

    # 1. Remove Service
    if [ -d "$servicePath" ]; then
        log_message "Removing service $serviceName"
        rm -rf "$servicePath"
    fi
    
    # 2. Kill process if running
    pkill -f "python3 $installPath/bms_aggregator.py" || true
    
    # 3. Remove files (Optional: keep config?)
    # For a full uninstall, we remove the data directory.
    # If users want to keep config, they should backup configs.
    if [ -d "$installPath" ]; then
        log_message "Removing installation directory $installPath"
        rm -rf "$installPath"
    fi
    
    log_message "Uninstallation complete."
}

# --- Main Execution ---

case "$ACTION" in
    install|reinstall)
        # For reinstall and install, we do the same: install overwrites
        install_package
        ;;
    uninstall)
        uninstall_package
        ;;
    *)
        echo "Usage: $0 {install|uninstall}"
        exit 1
        ;;
esac
