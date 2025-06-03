#!/bin/bash
# github_clone_setup.sh - Complete GitHub-like website installation script
# Usage: bash github_clone_setup.sh
# Make sure to run this script as a user with sudo privileges

# Exit on error
set -e

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}           GITHUB CLONE WEBSITE INSTALLATION               ${NC}"
echo -e "${GREEN}           Complete Self-Hosted Git Platform               ${NC}"
echo -e "${BLUE}============================================================${NC}"

# Check if running as root
if [ "$(id -u)" = "0" ]; then
   echo -e "${RED}This script should NOT be run as root${NC}"
   echo -e "${YELLOW}Please run as a regular user with sudo privileges${NC}"
   exit 1
fi

# Check if Ubuntu 22.04
if ! grep -q "Ubuntu 22.04" /etc/os-release; then
    echo -e "${YELLOW}This script is optimized for Ubuntu 22.04${NC}"
    echo -e "${YELLOW}Your system may not be fully compatible${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Generate secure passwords
echo -e "${BLUE}Generating secure passwords...${NC}"
ROOT_PASSWORD=$(openssl rand -base64 12)
GITEA_DB_PASSWORD=$(openssl rand -base64 12)
ADMIN_PASSWORD=$(openssl rand -base64 8)

# Save passwords
mkdir -p ~/github_clone
echo "ROOT_PASSWORD=$ROOT_PASSWORD" > ~/github_clone/credentials.env
echo "GITEA_DB_PASSWORD=$GITEA_DB_PASSWORD" >> ~/github_clone/credentials.env
echo "ADMIN_USERNAME=admin" >> ~/github_clone/credentials.env
echo "ADMIN_PASSWORD=$ADMIN_PASSWORD" >> ~/github_clone/credentials.env
echo "ADMIN_EMAIL=admin@example.com" >> ~/github_clone/credentials.env
chmod 600 ~/github_clone/credentials.env

echo -e "${GREEN}Secure credentials saved to ~/github_clone/credentials.env${NC}"
echo -e "${YELLOW}PLEASE KEEP THIS FILE SAFE!${NC}"

# Function to display progress
show_progress() {
    local step=$1
    local total=$2
    local description=$3
    local percentage=$((step * 100 / total))
    
    echo -e "${BLUE}[${step}/${total}]${NC} ${YELLOW}${percentage}%${NC} - ${description}..."
}

# 1. Update System
show_progress 1 12 "Updating system packages"
sudo apt update && sudo apt upgrade -y

# 2. Install Dependencies
show_progress 2 12 "Installing necessary packages"
sudo apt install -y git curl wget nginx mariadb-server certbot python3-certbot-nginx \
                   unzip supervisor software-properties-common ufw fail2ban

# 3. Set up Firewall
show_progress 3 12 "Configuring firewall"
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw --force enable

# 4. Configure MariaDB
show_progress 4 12 "Setting up database server"
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Secure MariaDB installation
sudo mysql -e "
ALTER USER 'root'@'localhost' IDENTIFIED BY '${ROOT_PASSWORD}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;"

# Create Gitea database and user
sudo mysql -u root -p"${ROOT_PASSWORD}" -e "
CREATE DATABASE giteadb CHARACTER SET 'utf8mb4' COLLATE 'utf8mb4_unicode_ci';
CREATE USER 'gitea'@'localhost' IDENTIFIED BY '${GITEA_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON giteadb.* TO 'gitea'@'localhost';
FLUSH PRIVILEGES;"

# 5. Create Git User
show_progress 5 12 "Creating git system user"
sudo adduser --system --shell /bin/bash --gecos 'Git Version Control' --group --disabled-password --home /home/git git

# 6. Setup Directories
show_progress 6 12 "Setting up Gitea directories"
sudo mkdir -p /var/lib/gitea/{custom,data,log}
sudo chown -R git:git /var/lib/gitea
sudo chmod -R 750 /var/lib/gitea
sudo mkdir -p /etc/gitea
sudo chown root:git /etc/gitea
sudo chmod 770 /etc/gitea

# 7. Download and Install Gitea
show_progress 7 12 "Downloading and installing Gitea"
VERSION=$(curl -s https://api.github.com/repos/go-gitea/gitea/releases/latest | grep tag_name | cut -d '"' -f 4 | cut -c 2-)
echo "Installing Gitea version ${VERSION}..."
sudo wget -O /usr/local/bin/gitea "https://dl.gitea.io/gitea/${VERSION}/gitea-${VERSION}-linux-amd64"
sudo chmod +x /usr/local/bin/gitea

# 8. Create Systemd Service
show_progress 8 12 "Creating systemd service"
sudo bash -c 'cat > /etc/systemd/system/gitea.service << EOF
[Unit]
Description=Gitea (Git with a cup of tea)
After=network.target
After=mysql.service
Requires=mysql.service

[Service]
User=git
Group=git
WorkingDirectory=/var/lib/gitea/
Environment=USER=git HOME=/home/git GITEA_WORK_DIR=/var/lib/gitea
ExecStart=/usr/local/bin/gitea web --config /etc/gitea/app.ini
Restart=always
RestartSec=2s
TimeoutStopSec=5s
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
EOF'

# 9. Configure Gitea
show_progress 9 12 "Creating Gitea configuration"

# Get server IP and hostname
SERVER_IP=$(hostname -I | awk '{print $1}')
SERVER_HOSTNAME=$(hostname)

# Ask user for domain
echo -e "${YELLOW}Please provide a domain name for your GitHub clone.${NC}"
echo -e "${YELLOW}Leave blank to use server IP (${SERVER_IP}) instead.${NC}"
read -p "Domain name: " DOMAIN_NAME

if [ -z "${DOMAIN_NAME}" ]; then
    DOMAIN_NAME=${SERVER_IP}
    USE_SSL=false
    echo -e "${YELLOW}Will use IP address ${SERVER_IP} (without HTTPS)${NC}"
else
    USE_SSL=true
    echo -e "${GREEN}Will configure with domain ${DOMAIN_NAME} and HTTPS${NC}"
fi

# Create app.ini configuration file
sudo bash -c "cat > /etc/gitea/app.ini << EOF
APP_NAME = GitHub Clone
RUN_USER = git
RUN_MODE = prod

[database]
DB_TYPE  = mysql
HOST     = 127.0.0.1:3306
NAME     = giteadb
USER     = gitea
PASSWD   = ${GITEA_DB_PASSWORD}
SSL_MODE = disable
CHARSET  = utf8mb4

[repository]
ROOT = /var/lib/gitea/data/gitea-repositories
DEFAULT_BRANCH = main
ENABLE_PUSH_CREATE_USER = true
ENABLE_PUSH_CREATE_ORG  = true

[server]
DOMAIN           = ${DOMAIN_NAME}
HTTP_PORT        = 3000
ROOT_URL         = http://${DOMAIN_NAME}/
DISABLE_SSH      = false
SSH_PORT         = 22
START_SSH_SERVER = false
SSH_LISTEN_PORT  = 22
LFS_START_SERVER = true
LFS_CONTENT_PATH = /var/lib/gitea/data/lfs
OFFLINE_MODE     = false

[security]
INSTALL_LOCK            = false
SECRET_KEY              = $(openssl rand -base64 32)
INTERNAL_TOKEN          = $(openssl rand -base64 32)
PASSWORD_HASH_ALGO      = pbkdf2

[service]
REGISTER_EMAIL_CONFIRM            = false
ENABLE_NOTIFY_MAIL                = false
DISABLE_REGISTRATION              = false
ALLOW_ONLY_EXTERNAL_REGISTRATION  = false
ENABLE_CAPTCHA                    = false
REQUIRE_SIGNIN_VIEW               = false
DEFAULT_KEEP_EMAIL_PRIVATE        = true
DEFAULT_ENABLE_TIMETRACKING       = true
NO_REPLY_ADDRESS                  = noreply@${DOMAIN_NAME}

[picture]
DISABLE_GRAVATAR        = false
ENABLE_FEDERATED_AVATAR = true

[openid]
ENABLE_OPENID_SIGNIN = true
ENABLE_OPENID_SIGNUP = true

[session]
PROVIDER = file
COOKIE_SECURE = false

[repository.pull-request]
DEFAULT_MERGE_STYLE = merge

[repository.issue]
ENABLED = true

[repository.upload]
ENABLED = true
TEMP_PATH = /var/lib/gitea/data/tmp/uploads
ALLOWED_TYPES = image/jpeg,image/png,image/gif,application/zip,application/gzip
MAX_SIZE = 10
MAX_FILES = 10

[log]
MODE      = file
LEVEL     = info
ROOT_PATH = /var/lib/gitea/log

[ui]
DEFAULT_THEME = gitea
THEMES = gitea,github-dark,github
THEME_COLOR_META_TAG = #6cc644
MAX_DISPLAY_FILE_SIZE = 8388608
SHOW_USER_EMAIL = false
EOF"

# 10. Configure Nginx
show_progress 10 12 "Setting up Nginx web server"

# Create Nginx config
sudo bash -c "cat > /etc/nginx/sites-available/gitea << EOF
server {
    listen 80;
    server_name ${DOMAIN_NAME};
    
    client_max_body_size 512M;
    
    access_log /var/log/nginx/gitea-access.log;
    error_log /var/log/nginx/gitea-error.log;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_max_temp_file_size 0;
        proxy_connect_timeout 90;
        proxy_send_timeout 90;
        proxy_read_timeout 90;
        proxy_buffer_size 4k;
        proxy_buffers 4 32k;
        proxy_busy_buffers_size 64k;
        proxy_temp_file_write_size 64k;
    }
}
EOF"

# Enable the site
sudo ln -sf /etc/nginx/sites-available/gitea /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx config
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# 11. Setup SSL (if domain provided)
if [ "$USE_SSL" = true ]; then
    show_progress 11 12 "Setting up SSL/HTTPS"
    
    # Install SSL certificate with Let's Encrypt
    sudo certbot --nginx -d ${DOMAIN_NAME} --non-interactive --agree-tos --email admin@${DOMAIN_NAME}
    
    # Update Gitea ROOT_URL configuration for HTTPS
    sudo sed -i "s|ROOT_URL         = http://|ROOT_URL         = https://|" /etc/gitea/app.ini
    sudo sed -i "s|COOKIE_SECURE = false|COOKIE_SECURE = true|" /etc/gitea/app.ini
else
    show_progress 11 12 "Skipping SSL setup (using HTTP)"
fi

# 12. Setup GitHub-like Theme
show_progress 12 12 "Setting up GitHub-like theme and customizations"

# Create custom CSS directory
sudo mkdir -p /var/lib/gitea/custom/public/css
sudo mkdir -p /var/lib/gitea/custom/public/img

# Create GitHub-like CSS
sudo bash -c "cat > /var/lib/gitea/custom/public/css/github-theme.css << 'EOF'
:root {
    --color-primary: #24292f;
    --color-primary-light: #2f363d;
    --color-primary-dark: #1b1f23;
    --color-secondary: #0366d6;
    --color-secondary-light: #2188ff;
    --color-secondary-dark: #044289;
    --color-background: #ffffff;
    --color-text: #24292e;
    --color-border: #e1e4e8;
    --color-header-bg: #24292f;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji';
}

.ui.top.menu {
    background-color: var(--color-header-bg);
}

.ui.menu .item {
    color: #fff;
}

.ui.button.primary {
    background-color: var(--color-secondary);
}

.ui.button.primary:hover {
    background-color: var(--color-secondary-dark);
}

.repository.header {
    background-color: var(--color-background);
    border-bottom: 1px solid var(--color-border);
}

.ui.tabular.menu {
    border-bottom: 1px solid var(--color-border);
}

.ui.tabular.menu .item.active {
    border-color: var(--color-secondary);
    color: var(--color-secondary);
}

.ui.secondary.menu .active.item {
    background-color: rgba(3, 102, 214, 0.1);
    color: #0366d6;
}

.feeds .list ul li:not(:last-child) {
    border-bottom: 1px solid var(--color-border);
}

.ui.attached.header {
    background: #f6f8fa;
    border-color: var(--color-border);
}

.ui.attached.table {
    border-color: var(--color-border);
}

.markdown h1, 
.markdown h2, 
.markdown h3, 
.markdown h4, 
.markdown h5, 
.markdown h6 {
    font-weight: 600;
    margin-top: 24px;
    margin-bottom: 16px;
}

.markdown h1, 
.markdown h2 {
    border-bottom: 1px solid #eaecef;
    padding-bottom: 0.3em;
}
EOF"

# Fix permissions
sudo chown -R git:git /var/lib/gitea/custom
sudo chmod -R 755 /var/lib/gitea/custom

# Add theme to app.ini if not already there
if ! grep -q "INCLUDE_GITHUB_CSS" /etc/gitea/app.ini; then
    sudo bash -c "cat >> /etc/gitea/app.ini << EOF
    
[ui.css]
INCLUDE_GITHUB_CSS = true
EXTRA_FILE_LIST = /css/github-theme.css
EOF"
fi

# Enable and start Gitea
echo -e "${BLUE}Starting Gitea service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable gitea
sudo systemctl start gitea

# Wait for Gitea to start
echo -e "${YELLOW}Waiting for Gitea to start up...${NC}"
sleep 10

# Create Gitea admin user automatically
if curl -s http://localhost:3000/ | grep -q "install"; then
    echo -e "${GREEN}Performing initial Gitea setup automatically...${NC}"
    
    # Get CSRF token
    CSRF_TOKEN=$(curl -s http://localhost:3000/install | grep -oP '(?<=_csrf" content=")[^"]*')
    
    if [ -z "$CSRF_TOKEN" ]; then
        echo -e "${RED}Failed to get CSRF token. Manual setup required.${NC}"
    else
        # Perform installation via API
        curl -s -X POST http://localhost:3000/install \
          -H "Content-Type: application/x-www-form-urlencoded" \
          -d "_csrf=${CSRF_TOKEN}" \
          -d "db_type=mysql" \
          -d "db_host=127.0.0.1:3306" \
          -d "db_name=giteadb" \
          -d "db_user=gitea" \
          -d "db_passwd=${GITEA_DB_PASSWORD}" \
          -d "ssl_mode=disable" \
          -d "charset=utf8mb4" \
          -d "app_name=GitHub Clone" \
          -d "repo_root_path=/var/lib/gitea/data/gitea-repositories" \
          -d "lfs_root_path=/var/lib/gitea/data/lfs" \
          -d "run_user=git" \
          -d "domain=${DOMAIN_NAME}" \
          -d "ssh_port=22" \
          -d "http_port=3000" \
          -d "app_url=$([ "$USE_SSL" = true ] && echo "https" || echo "http")://${DOMAIN_NAME}/" \
          -d "log_root_path=/var/lib/gitea/log" \
          -d "admin_name=admin" \
          -d "admin_passwd=${ADMIN_PASSWORD}" \
          -d "admin_confirm_passwd=${ADMIN_PASSWORD}" \
          -d "admin_email=admin@example.com"
          
        echo -e "${GREEN}Installation completed automatically!${NC}"
    fi
else
    echo -e "${YELLOW}Gitea is already installed.${NC}"
fi

# Create maintenance scripts
mkdir -p ~/github_clone/scripts

# Backup script
cat > ~/github_clone/scripts/backup.sh << EOF
#!/bin/bash
