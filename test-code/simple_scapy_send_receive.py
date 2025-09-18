#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import threading
import queue
import subprocess
import os
import signal
from scapy.all import *

class PacketSenderReceiver:
    def __init__(self):
        self.interface = "fp0"
        self.source_ip = "100.1.1.1"
        self.source_mac = "00:00:00:00:11:11"
        self.dest_ip = "100.1.1.2"
        self.dest_mac = "00:00:00:00:22:22"
        self.data_size = 100
        self.packet_count = 2
        
        # 수신된 패킷을 저장할 큐
        self.received_packets = queue.Queue()
        self.sending = False
        self.receiving = False
        
        # tcpdump 프로세스 관리
        self.tcpdump_process = None
        self.pcap_file = "/tmp/inbound.pcap"
        
        # 스위치 테스트용 허용된 source IP/MAC 조합
        self.allowed_sources = {
            "00:00:00:00:11:11": "100.1.1.1",
            "00:00:00:00:22:22": "100.1.1.2", 
            "00:00:00:00:33:33": "100.1.1.3",
            "00:00:00:00:44:44": "100.1.1.4"
        }
        
    def create_packet(self):
        """패킷 생성"""
        test_data = b"X" * self.data_size
        packet = Ether(src=self.source_mac, dst=self.dest_mac) / \
                 IP(src=self.source_ip, dst=self.dest_ip) / \
                 Raw(test_data)
        return packet
    
    def start_tcpdump_pipe(self):
        """tcpdump를 파이프로 시작하여 실시간 처리"""
        try:
            # tcpdump 명령어 구성 (-Q in: inbound만 캡처, -U: unbuffered)
            cmd = [
                "tcpdump", 
                "-i", self.interface,
                "-Q", "in",  # inbound만 캡처
                "-U",        # unbuffered 출력
                "-w", "-",   # stdout으로 출력
                "-n"         # DNS 해석 비활성화
            ]
            
            print(f"[tcpdump] 파이프 시작: {' '.join(cmd)}")
            self.tcpdump_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # tcpdump가 시작될 때까지 잠시 대기
            time.sleep(1)
            
            if self.tcpdump_process.poll() is None:
                print(f"[tcpdump] 파이프 성공적으로 시작됨 (PID: {self.tcpdump_process.pid})")
                return True
            else:
                print(f"[tcpdump] 파이프 시작 실패")
                return False
                
        except Exception as e:
            print(f"[tcpdump] 파이프 시작 오류: {e}")
            return False
    
    def stop_tcpdump(self):
        """tcpdump 프로세스 중지"""
        try:
            if self.tcpdump_process and self.tcpdump_process.poll() is None:
                print(f"[tcpdump] 중지 중...")
                # 프로세스 그룹 전체 종료
                os.killpg(os.getpgid(self.tcpdump_process.pid), signal.SIGTERM)
                self.tcpdump_process.wait(timeout=5)
                
                # tcpdump 출력 확인 (stderr만 텍스트)
                stderr_output = self.tcpdump_process.stderr.read().decode()
                if stderr_output:
                    print(f"[tcpdump] stderr: {stderr_output}")
                # stdout은 바이너리 데이터이므로 출력하지 않음
                
                print(f"[tcpdump] 중지 완료")
        except Exception as e:
            print(f"[tcpdump] 중지 오류: {e}")
    
    def read_pcap_packets(self):
        """pcap 파일에서 패킷 읽기"""
        try:
            if not os.path.exists(self.pcap_file):
                print(f"[pcap] 파일이 존재하지 않음: {self.pcap_file}")
                return
            
            from scapy.all import PcapReader
            
            packet_count = 0
            for packet in PcapReader(self.pcap_file):
                packet_count += 1
                self.process_inbound_packet(packet)
            
            print(f"[pcap] 총 {packet_count}개 패킷 처리 완료")
            
        except Exception as e:
            print(f"[pcap] 읽기 오류: {e}")
    
    def read_pipe_packets(self):
        """파이프에서 실시간으로 패킷 읽기"""
        try:
            from scapy.all import PcapReader
            import io
            
            packet_count = 0
            # stdout을 바이너리 스트림으로 읽기
            stdout_data = self.tcpdump_process.stdout.read()
            
            if stdout_data:
                # 바이너리 데이터를 BytesIO로 변환하여 PcapReader로 읽기
                pcap_stream = io.BytesIO(stdout_data)
                for packet in PcapReader(pcap_stream):
                    packet_count += 1
                    self.process_inbound_packet(packet)
            
            print(f"[파이프] 총 {packet_count}개 패킷 처리 완료")
            
        except Exception as e:
            print(f"[파이프] 읽기 오류: {e}")
    
    def process_inbound_packet(self, packet):
        """inbound 패킷 처리 - 허용된 source IP/MAC 조합만 수신"""
        try:
            # 패킷에서 source MAC과 IP 추출
            src_mac = None
            src_ip = None
            
            if packet.haslayer(Ether):
                src_mac = packet[Ether].src
                dst_mac = packet[Ether].dst
            
            if packet.haslayer(IP):
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst
            
            # 허용된 source IP/MAC 조합인지 확인
            if src_mac and src_ip:
                if src_mac in self.allowed_sources and self.allowed_sources[src_mac] == src_ip:
                    # 허용된 패킷 - 수신된 패킷을 큐에 저장
                    self.received_packets.put({
                        'time': time.time(),
                        'packet': packet,
                        'size': len(packet)
                    })
                    
                    # 패킷 정보 출력
                    print(f"\n[수신] {time.strftime('%H:%M:%S.%f')[:-3]} - 허용된 inbound 패킷")
                    print(f"  MAC: {src_mac} -> {dst_mac}")
                    print(f"  IP: {src_ip} -> {dst_ip}")
                    
                    if packet.haslayer(Raw):
                        data_size = len(packet[Raw].load)
                        print(f"  데이터: {data_size}바이트")
                    
                    print(f"  크기: {len(packet)}바이트")
                else:
                    # 허용되지 않은 패킷 - 무시
                    print(f"[무시] {time.strftime('%H:%M:%S.%f')[:-3]} - 허용되지 않은 source")
                    print(f"  MAC: {src_mac}, IP: {src_ip}")
            else:
                # IP 레이어가 없는 패킷 - 무시
                print(f"[무시] {time.strftime('%H:%M:%S.%f')[:-3]} - IP 레이어 없음")
            
        except Exception as e:
            print(f"패킷 처리 오류: {e}")
    
    def receiver_thread(self):
        """tcpdump 파이프를 사용한 실시간 inbound 패킷 수신 스레드"""
        print(f"[수신] tcpdump 파이프를 사용한 실시간 inbound 패킷 수신 시작...")
        self.receiving = True
        
        try:
            # tcpdump 파이프 시작
            if not self.start_tcpdump_pipe():
                print("[수신] tcpdump 파이프 시작 실패")
                return
            
            # 수신 대기 (전송이 완료될 때까지)
            while self.sending:
                time.sleep(0.1)
            
            # 추가 대기 (패킷이 도착할 시간을 줌)
            time.sleep(2)
            
            # tcpdump 중지
            self.stop_tcpdump()
            
            # 파이프에서 패킷 읽기 (파일 없이)
            self.read_pipe_packets()
            
        except Exception as e:
            print(f"[수신] 오류: {e}")
        finally:
            self.receiving = False
            print("[수신] 수신 스레드 종료")
    
    def sender_thread(self):
        """패킷 전송 스레드"""
        print(f"[전송] {self.packet_count}개 패킷 전송 시작...")
        self.sending = True
        
        try:
            # 패킷 생성
            packet = self.create_packet()
            print(f"[전송] 패킷 크기: {len(packet)}바이트")
            
            # 전송 시작
            start_time = time.time()
            sendp(packet, iface=self.interface, verbose=False, count=self.packet_count)
            end_time = time.time()
            
            total_time = end_time - start_time
            print(f"[전송] {self.packet_count}개 패킷 전송 완료!")
            print(f"[전송] 전송 시간: {total_time:.3f}초")
            print(f"[전송] 초당 패킷 수: {self.packet_count/total_time:.1f} pps")
            
        except Exception as e:
            print(f"[전송] 오류: {e}")
        finally:
            self.sending = False
            print("[전송] 전송 스레드 종료")
    
    def run_send_and_receive(self):
        """전송과 수신을 동시에 실행"""
        print("=" * 60)
        print("패킷 전송 및 동시 수신 시작 (tcpdump 파이프 방식)")
        print(f"인터페이스: {self.interface}")
        print(f"전송 횟수: {self.packet_count}개")
        print(f"패킷 크기: {self.data_size}바이트")
        print("=" * 60)
        
        # 수신 스레드 시작
        receiver = threading.Thread(target=self.receiver_thread, daemon=False)
        receiver.start()
        
        # 수신이 시작될 때까지 잠시 대기
        time.sleep(1)
        
        # 전송 스레드 시작
        sender = threading.Thread(target=self.sender_thread)
        sender.start()
        
        # 전송 완료까지 대기
        sender.join()
        
        # 수신 스레드 완료까지 대기
        receiver.join()
        
        # 수신된 패킷 통계 출력
        self.print_receive_statistics()
        
        print("\n프로그램 종료")
    
    def print_receive_statistics(self):
        """수신 통계 출력"""
        received_count = self.received_packets.qsize()
        print(f"\n=== 수신 통계 ===")
        print(f"수신된 패킷 수: {received_count}개")
        
        if received_count > 0:
            packets = []
            while not self.received_packets.empty():
                packets.append(self.received_packets.get())
            
            if len(packets) > 1:
                first_time = packets[0]['time']
                last_time = packets[-1]['time']
                total_time = last_time - first_time
                print(f"수신 시간 범위: {total_time:.3f}초")
                print(f"수신 속도: {len(packets)/total_time:.1f} pps")
            
            # 패킷 크기 통계
            sizes = [p['size'] for p in packets]
            print(f"평균 패킷 크기: {sum(sizes)/len(sizes):.1f}바이트")
            print(f"최소 패킷 크기: {min(sizes)}바이트")
            print(f"최대 패킷 크기: {max(sizes)}바이트")

def main():
    """메인 함수"""
    sender_receiver = PacketSenderReceiver()
    
    try:
        sender_receiver.run_send_and_receive()
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    main()