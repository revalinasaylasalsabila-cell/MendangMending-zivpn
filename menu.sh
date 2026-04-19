#!/bin/bash
# ZIVPN MENU MANAGER - MendangMending.co

# === Konfigurasi Warna ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Mengambil IP VPS
IP=$(curl -s ifconfig.me)
DOMAIN="men-ding.nevpn.biz.id"

# === Fungsi Tambah Akun ===
function add_account() {
    clear
    echo -e "${YELLOW}======================================${NC}"
    echo -e "${GREEN}             ADD ACCOUNT              ${NC}"
    echo -e "${YELLOW}======================================${NC}"
    read -p "Username : " user
    read -p "Password : " pass
    read -p "Expired (Hari) : " exp
    
    # Menghitung tanggal expired
    exp_date=$(date -d "+$exp days" +"%Y-%m-%d")
    
    # (Di sinilah nanti logika untuk memasukkan password ke config.json ZIVPN ditambahkan)
    
    clear
    echo -e "${CYAN}======================================${NC}"
    echo -e "${YELLOW}          NEW ACCOUNT ADDED           ${NC}"
    echo -e "${CYAN}======================================${NC}"
    echo -e "User     : ${CYAN}$user${NC}"
    echo -e "Password : ${GREEN}$pass${NC}"
    echo -e "Expired  : ${CYAN}$exp_date${NC}"
    echo -e "Server   : ${CYAN}$IP${NC}"
    echo -e "${CYAN}======================================${NC}"
    echo -e "${MAGENTA}▶ Account added successfully!${NC}"
    echo ""
    read -p "$(echo -e "${GREEN}Press ENTER to continue...${NC}")"
    menu
}

# === Menu Utama ===
function menu() {
    clear
    echo -e "${MAGENTA}  __  __                  _                  ${NC}"
    echo -e "${MAGENTA} |  \/  | ___ _ __   __ _| |__  _   _        ${NC}"
    echo -e "${MAGENTA} | |\/| |/ _ \ '_ \ / _\` | '_ \| | | |     ${NC}"
    echo -e "${MAGENTA} | |  | |  __/ | | | (_| | | | | |_| |       ${NC}"
    echo -e "${MAGENTA} |_|  |_|\___|_| |_|\__,_|_| |_|\__,_|       ${NC}"
    echo -e "${CYAN}=============================================${NC}"
    echo -e "${YELLOW}===========[ ZIVPN MANAGER V 1.0 ]===========${NC}"
    echo -e ""
    echo -e " 🌐 ${CYAN}IP Server : < $IP >${NC}"
    echo -e " 🌍 ${CYAN}Domain    : $DOMAIN${NC}"
    echo -e "${YELLOW}=============================================${NC}"
    echo -e " || ${YELLOW}ACCOUNT MANAGER </>${NC}"
    echo -e "${YELLOW}=============================================${NC}"
    echo -e ""
    echo -e " ${CYAN}[1]${NC} ${YELLOW}Add Account${NC}          ${CYAN}[4]${NC} ${YELLOW}Renew Account${NC}"
    echo -e " ${CYAN}[2]${NC} ${YELLOW}Trial Account${NC}        ${CYAN}[5]${NC} ${YELLOW}Change Password${NC}"
    echo -e " ${CYAN}[3]${NC} ${YELLOW}Delete Account${NC}       ${CYAN}[6]${NC} ${YELLOW}List Accounts${NC}"
    echo -e ""
    echo -e " ${CYAN}[0]${NC} ${YELLOW}Exit${NC}"
    echo -e "${CYAN}=============================================${NC}"
    echo -e ""
    read -p "$(echo -e "${CYAN}//_> Choose an option: ${NC}") " opt

    case $opt in
        1) add_account ;;
        2) echo "Fitur Trial sedang dibuat..."; sleep 2; menu ;;
        3) echo "Fitur Delete sedang dibuat..."; sleep 2; menu ;;
        0) clear; exit 0 ;;
        *) echo -e "${RED}Pilihan tidak valid!${NC}"; sleep 1; menu ;;
    esac
}

# Menjalankan fungsi menu
menu
