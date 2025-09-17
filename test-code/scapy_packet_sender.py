#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scapy를 사용하여 지정된 소스와 목적지로 패킷을 전송하는 스크립트
"""

from scapy.all import *
import time
import sys
import os

def send_custom_packet():
    """지정된 소스와 목적지로 임의의 패킷을 전송"""
    
    # 네트워크 인터페이스 설정
    interface = "py_phy0"
    
    # 소스 정보
    source_ip = "100.1.1.1"
    source_mac = "00:00:00:00:11:11"
    
    # 목적지 정보
    dest_ip = "100.1.1.2"
    dest_mac = "00:00:00:00:22:22"
    
    print(f"=== Scapy 패킷 전송 스크립트 ===")
    print(f"인터페이스: {interface}")
    print(f"소스 IP: {source_ip}")
    print(f"소스 MAC: {source_mac}")
    print(f"목적지 IP: {dest_ip}")
    print(f"목적지 MAC: {dest_mac}")
    print()
    
    try:
        # 패킷 생성 (Ethernet + IP + ICMP)
        packet = Ether(src=source_mac, dst=dest_mac) / \
                 IP(src=source_ip, dst=dest_ip) / \
                 ICMP(type=8, code=0) / \
                 Raw(b"Hello from Scapy!")
        
        print("생성된 패킷:")
        packet.show()
        print()
        
        # 패킷 전송
        print(f"패킷을 {interface} 인터페이스로 전송 중...")
        
        # 단일 패킷 전송
        sendp(packet, iface=interface, verbose=True)
        
        print("패킷 전송 완료!")
        
        # 여러 패킷 전송 (옵션)
        print("\n연속 패킷 전송을 시작합니다... (Ctrl+C로 중지)")
        count = 0
        
        while True:
            try:
                # 각 패킷마다 다른 데이터 추가
                custom_data = f"Packet #{count} - Timestamp: {time.time()}"
                packet = Ether(src=source_mac, dst=dest_mac) / \
                         IP(src=source_ip, dst=dest_ip) / \
                         ICMP(type=8, code=0) / \
                         Raw(custom_data.encode())
                
                sendp(packet, iface=interface, verbose=False)
                count += 1
                
                print(f"패킷 #{count} 전송 완료")
                time.sleep(1)  # 1초 간격으로 전송
                
            except KeyboardInterrupt:
                print(f"\n전송 중단됨. 총 {count}개 패킷 전송 완료.")
                break
                
    except Exception as e:
        print(f"패킷 전송 중 오류 발생: {e}")
        return False
    
    return True

def send_custom_tcp_packet():
    """TCP 패킷을 전송하는 함수"""
    
    interface = "py_phy0"
    source_ip = "100.1.1.1"
    source_mac = "00:00:00:00:11:11"
    dest_ip = "100.1.1.2"
    dest_mac = "00:00:00:00:22:22"
    
    print(f"=== TCP 패킷 전송 ===")
    
    try:
        # TCP 패킷 생성
        packet = Ether(src=source_mac, dst=dest_mac) / \
                 IP(src=source_ip, dst=dest_ip) / \
                 TCP(sport=12345, dport=80, flags="S") / \
                 Raw(b"TCP SYN packet from Scapy")
        
        print("TCP 패킷 생성:")
        packet.show()
        print()
        
        # TCP 패킷 전송
        sendp(packet, iface=interface, verbose=True)
        print("TCP 패킷 전송 완료!")
        
    except Exception as e:
        print(f"TCP 패킷 전송 중 오류 발생: {e}")

def send_custom_udp_packet():
    """UDP 패킷을 전송하는 함수"""
    
    interface = "py_phy0"
    source_ip = "100.1.1.1"
    source_mac = "00:00:00:00:11:11"
    dest_ip = "100.1.1.2"
    dest_mac = "00:00:00:00:22:22"
    
    print(f"=== UDP 패킷 전송 ===")
    
    try:
        # UDP 패킷 생성
        packet = Ether(src=source_mac, dst=dest_mac) / \
                 IP(src=source_ip, dst=dest_ip) / \
                 UDP(sport=12345, dport=53) / \
                 Raw(b"UDP packet from Scapy")
        
        print("UDP 패킷 생성:")
        packet.show()
        print()
        
        # UDP 패킷 전송
        sendp(packet, iface=interface, verbose=True)
        print("UDP 패킷 전송 완료!")
        
    except Exception as e:
        print(f"UDP 패킷 전송 중 오류 발생: {e}")

def main():
    """메인 함수"""
    print("Scapy 패킷 전송 도구")
    print("1. ICMP 패킷 전송")
    print("2. TCP 패킷 전송")
    print("3. UDP 패킷 전송")
    print("4. 모든 패킷 전송")
    
    try:
        choice = input("\n선택하세요 (1-4): ").strip()
        
        if choice == "1":
            send_custom_packet()
        elif choice == "2":
            send_custom_tcp_packet()
        elif choice == "3":
            send_custom_udp_packet()
        elif choice == "4":
            print("모든 패킷 타입을 전송합니다...")
            send_custom_packet()
            time.sleep(2)
            send_custom_tcp_packet()
            time.sleep(2)
            send_custom_udp_packet()
        else:
            print("잘못된 선택입니다.")
            
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    # 관리자 권한 확인
    if os.geteuid() != 0:
        print("이 스크립트는 관리자 권한(root)으로 실행해야 합니다.")
        print("sudo python3 scapy_packet_sender.py")
        sys.exit(1)
    
    main()