#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고급 Scapy 패킷 전송 스크립트 - 다양한 패킷 타입과 옵션 제공
"""

from scapy.all import *
import subprocess
import re
import time
import sys
import os

def get_available_interfaces():
    """사용 가능한 네트워크 인터페이스 목록을 가져옴"""
    try:
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
        interfaces = []
        for line in result.stdout.split('\n'):
            if ': ' in line and 'state' in line:
                match = re.search(r'^\d+: (\w+):', line)
                if match:
                    interface_name = match.group(1)
                    if interface_name != 'lo':
                        interfaces.append(interface_name)
        return interfaces
    except Exception as e:
        print(f"인터페이스 목록을 가져오는 중 오류: {e}")
        return []

def send_icmp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, count=1):
    """ICMP 패킷 전송"""
    print(f"\n=== ICMP 패킷 전송 ===")
    
    for i in range(count):
        try:
            packet = Ether(src=source_mac, dst=dest_mac) / \
                     IP(src=source_ip, dst=dest_ip) / \
                     ICMP(type=8, code=0) / \
                     Raw(f"ICMP Packet #{i+1} - {time.time()}".encode())
            
            sendp(packet, iface=interface, verbose=False)
            print(f"ICMP 패킷 #{i+1} 전송 완료")
            
            if count > 1:
                time.sleep(1)
                
        except Exception as e:
            print(f"ICMP 패킷 #{i+1} 전송 실패: {e}")

def send_tcp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, count=1):
    """TCP 패킷 전송"""
    print(f"\n=== TCP 패킷 전송 ===")
    
    for i in range(count):
        try:
            packet = Ether(src=source_mac, dst=dest_mac) / \
                     IP(src=source_ip, dst=dest_ip) / \
                     TCP(sport=12345+i, dport=80, flags="S") / \
                     Raw(f"TCP SYN Packet #{i+1} - {time.time()}".encode())
            
            sendp(packet, iface=interface, verbose=False)
            print(f"TCP 패킷 #{i+1} 전송 완료")
            
            if count > 1:
                time.sleep(1)
                
        except Exception as e:
            print(f"TCP 패킷 #{i+1} 전송 실패: {e}")

def send_udp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, count=1):
    """UDP 패킷 전송"""
    print(f"\n=== UDP 패킷 전송 ===")
    
    for i in range(count):
        try:
            packet = Ether(src=source_mac, dst=dest_mac) / \
                     IP(src=source_ip, dst=dest_ip) / \
                     UDP(sport=12345+i, dport=53) / \
                     Raw(f"UDP Packet #{i+1} - {time.time()}".encode())
            
            sendp(packet, iface=interface, verbose=False)
            print(f"UDP 패킷 #{i+1} 전송 완료")
            
            if count > 1:
                time.sleep(1)
                
        except Exception as e:
            print(f"UDP 패킷 #{i+1} 전송 실패: {e}")

def send_arp_packet(interface, source_ip, source_mac, dest_ip, dest_mac):
    """ARP 패킷 전송"""
    print(f"\n=== ARP 패킷 전송 ===")
    
    try:
        # ARP Request 패킷
        arp_request = Ether(src=source_mac, dst="ff:ff:ff:ff:ff:ff") / \
                      ARP(hwsrc=source_mac, psrc=source_ip, hwdst="00:00:00:00:00:00", pdst=dest_ip)
        
        sendp(arp_request, iface=interface, verbose=False)
        print("ARP Request 패킷 전송 완료")
        
        # ARP Reply 패킷
        arp_reply = Ether(src=source_mac, dst=dest_mac) / \
                    ARP(hwsrc=source_mac, psrc=source_ip, hwdst=dest_mac, pdst=dest_ip, op=2)
        
        sendp(arp_reply, iface=interface, verbose=False)
        print("ARP Reply 패킷 전송 완료")
        
    except Exception as e:
        print(f"ARP 패킷 전송 실패: {e}")

def main():
    """메인 함수"""
    print("=== 고급 Scapy 패킷 전송 도구 ===")
    
    # 사용 가능한 인터페이스 확인
    available_interfaces = get_available_interfaces()
    print("\n사용 가능한 인터페이스:")
    for i, iface in enumerate(available_interfaces):
        print(f"  {i+1}. {iface}")
    
    # 인터페이스 선택
    preferred_interface = "fp_phy0"
    if preferred_interface in available_interfaces:
        interface = preferred_interface
        print(f"\n자동 선택된 인터페이스: {interface}")
    elif available_interfaces:
        interface = available_interfaces[0]
        print(f"\n자동 선택된 인터페이스: {interface}")
    else:
        print("사용 가능한 인터페이스가 없습니다!")
        return
    
    # 네트워크 설정
    source_ip = "100.1.1.1"
    source_mac = "00:00:00:00:11:11"
    dest_ip = "100.1.1.2"
    dest_mac = "00:00:00:00:22:22"
    
    print(f"\n네트워크 설정:")
    print(f"  소스: {source_ip} ({source_mac})")
    print(f"  목적지: {dest_ip} ({dest_mac})")
    
    # 메뉴 표시
    while True:
        print(f"\n=== 패킷 전송 메뉴 ===")
        print("1. ICMP 패킷 전송 (1개)")
        print("2. ICMP 패킷 전송 (5개)")
        print("3. TCP 패킷 전송 (1개)")
        print("4. TCP 패킷 전송 (5개)")
        print("5. UDP 패킷 전송 (1개)")
        print("6. UDP 패킷 전송 (5개)")
        print("7. ARP 패킷 전송")
        print("8. 모든 패킷 타입 전송")
        print("9. 종료")
        
        try:
            choice = input("\n선택하세요 (1-9): ").strip()
            
            if choice == "1":
                send_icmp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, 1)
            elif choice == "2":
                send_icmp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, 5)
            elif choice == "3":
                send_tcp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, 1)
            elif choice == "4":
                send_tcp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, 5)
            elif choice == "5":
                send_udp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, 1)
            elif choice == "6":
                send_udp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, 5)
            elif choice == "7":
                send_arp_packet(interface, source_ip, source_mac, dest_ip, dest_mac)
            elif choice == "8":
                print("모든 패킷 타입을 전송합니다...")
                send_icmp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, 1)
                time.sleep(1)
                send_tcp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, 1)
                time.sleep(1)
                send_udp_packet(interface, source_ip, source_mac, dest_ip, dest_mac, 1)
                time.sleep(1)
                send_arp_packet(interface, source_ip, source_mac, dest_ip, dest_mac)
            elif choice == "9":
                print("프로그램을 종료합니다.")
                break
            else:
                print("잘못된 선택입니다. 1-9 중에서 선택하세요.")
                
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")

if __name__ == "__main__":
    # 관리자 권한 확인
    if os.geteuid() != 0:
        print("이 스크립트는 관리자 권한(root)으로 실행해야 합니다.")
        print("sudo python3 advanced_scapy_sender.py")
        sys.exit(1)
    
    main()
