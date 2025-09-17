/****************************************************************************************
 *   FileName    : axon-ipc-dev.c
 *   Description : axon-ipc-dev.c
 ****************************************************************************************
 *
 *   AXON Version 1.0
 *   Copyright (c) Telechips Inc.
 *   All rights reserved

This source code contains confidential information of Telechips.
Any unauthorized use without a written permission of Telechips including not limited
to re-distribution in source or binary form is strictly prohibited.
This source code is provided ��AS IS�� and nothing contained in this source code
shall constitute any express or implied warranty of any kind, including without limitation,
any warranty of merchantability, fitness for a particular purpose or non-infringement of any patent,
copyright or other third party intellectual property right.
No warranty is made, express or implied, regarding the information��s accuracy,
completeness, or performance.
In no event shall Telechips be liable for any claim, damages or other liability arising from,
out of or in connection with this source code or the use in the source code.
This source code is provided subject to the terms of a Mutual Non-Disclosure Agreement
between Telechips and Company.
*
****************************************************************************************/
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdint.h>
#include <stdlib.h>
#include <poll.h>

#include "axon_ipc.h"
#include "axon-ipc-ctrl-log.h"
#include "axon-ipc-dev.h"

static int32_t ipc_ping_test(axon_ipc_ping_info *pingInfo);

static int32_t fd0 = -1;
static int32_t fd1 = -1;
static int32_t fd2 = -1;
static int32_t fd3 = -1;

unsigned char readBuf0[512];
unsigned char readBuf1[512];
unsigned char readBuf2[512];
unsigned char readBuf3[512];

char writeBuf[512] = {0,};

uint8_t CetracSend[512];


void parse_data_frame(const uint8_t *buffer, uint16_t data_length)
{
	uint16_t i;
	RX_DATA_FRAME data_frame;

	uint8_t rx_frame_type;
	uint8_t rx_sourcePort;
	uint16_t rx_timeStamp_ns;
	uint32_t rx_timeStamp_us_L;
	uint32_t rx_timeStamp_us_H;
	uint8_t rx_protocol_type;
	uint16_t rx_can_id;
	uint16_t rx_lin_id;
	uint32_t rx_extCan_id;
	uint8_t rx_fdf;
	uint8_t rx_rtr;
	uint8_t rx_ide;
	uint32_t route_id;

    //mcu_printf("%s_%d\n", __func__, __LINE__);
	rx_frame_type = buffer[0] & 0x01U;
	rx_sourcePort = ((buffer[0] & 0xFEU) >> 1U) + ((buffer[1] & 0x01U) << 7U);

	rx_timeStamp_ns  = (((uint16_t)buffer[1] & 0xFEU) >> 1U);
	rx_timeStamp_ns |= (((uint16_t)buffer[2] & 0x01U) << 7U);
	rx_timeStamp_ns *= 10U;

	rx_timeStamp_us_L = ((uint32_t)buffer[2] >> 1U);
	rx_timeStamp_us_L |= ((uint32_t)buffer[3] << 7U);
	rx_timeStamp_us_L |= ((uint32_t)buffer[4] << 15U);
	rx_timeStamp_us_L |= ((uint32_t)buffer[5] << 23U);
	rx_timeStamp_us_L |= (((uint32_t)buffer[6] & 0x01U) << 31U);
	rx_timeStamp_us_H = ((uint32_t)buffer[6] >> 1U);
	rx_timeStamp_us_H |= ((uint32_t)buffer[7] << 7U);
	rx_timeStamp_us_H |= ((uint32_t)buffer[8] << 15U);
	rx_timeStamp_us_H |= ((uint32_t)buffer[9] << 23U);
	rx_timeStamp_us_H |= (((uint32_t)buffer[10] & 0x01U) << 31U);

	rx_protocol_type = ((buffer[10] & 0x80U) == 0x80U)?1U:0U;

	rx_can_id = (uint16_t)buffer[11] + (((uint16_t)buffer[12] & 0x07U) << 8U);
	rx_lin_id = (uint16_t)buffer[11] & 0x3FU;
	rx_extCan_id  = (uint32_t)buffer[11];
	rx_extCan_id |= ((uint32_t)buffer[12] << 8U);
	rx_extCan_id |= ((uint32_t)buffer[13] << 16U);
	rx_extCan_id |= (((uint32_t)buffer[14] & 0x1FU) << 24U);


	rx_fdf = ((buffer[14] & 0x20U) == 0x20U)?1U:0U;
	rx_rtr = ((buffer[14] & 0x40U) == 0x40U)?1U:0U;
	rx_ide = ((buffer[14] & 0x80U) == 0x80U)?1U:0U;

    //mcu_printf("%s_%d type = %d\n", __func__, __LINE__, rx_frame_type);
	if (rx_frame_type == DATA_FRAME)
	{
		data_frame.port = rx_sourcePort;
		data_frame.proto = rx_protocol_type;
		data_frame.ts_us_high = rx_timeStamp_us_H;
		data_frame.ts_us_low = rx_timeStamp_us_L;
		data_frame.ts_ns = rx_timeStamp_ns;

		for(i = 15U; i < data_length; i++)
		{
			data_frame.Data[i-15U] = buffer[i];
 		}
		i = data_length - 15U;
		if (i <= 255U)
		{
			data_frame.data_len = (uint8_t)i;
		}
		else
		{
			data_frame.data_len = 8U;
		}
		if (rx_protocol_type == PROTOCOL_CAN)
		{
			if (rx_ide == STANDARD_CAN)
			{
				data_frame.ftype = FRAME_TYPE_CAN_BASE;
				if (rx_fdf == CAN_FD)
				{
					data_frame.ftype = FRAME_TYPE_CANFD_BASE;
				}
				data_frame.ID = rx_can_id;
                route_id = data_frame.ID;
			}
			else
			{
				data_frame.ftype = FRAME_TYPE_CAN_EXT;
				if (rx_fdf == CAN_FD)
				{
					data_frame.ftype = FRAME_TYPE_CANFD_EXT;
				}
				data_frame.ID = rx_extCan_id;
                route_id = (data_frame.ID | 0x80000000);
			}
		}
		else
		{
			data_frame.ftype = FRAME_TYPE_LIN_RX;
			data_frame.ID = rx_lin_id;
		}

		printf(" ======== PROC Data Frame====================\n");
		printf(" Protocol: %s, Port:%s, data_len:%d\n",
			(data_frame.proto == PROTOCOL_CAN)?"CAN":"LIN",
			PORT_NAME[data_frame.port],
			data_frame.data_len);

		switch(data_frame.ftype)
		{
			case FRAME_TYPE_CAN_BASE:
				printf(" CAN_ID:0x%X\n", data_frame.ID);
				break;
			case FRAME_TYPE_CAN_EXT:
				printf(" CAN_ID(ext):0x%X\n", data_frame.ID);
				break;
			case FRAME_TYPE_CANFD_BASE:
				printf(" CANFD_ID:0x%X\n", data_frame.ID);
				break;
			case FRAME_TYPE_CANFD_EXT:
				printf(" CANFD_ID(ext):0x%X\n", data_frame.ID);
				break;
			case FRAME_TYPE_LIN_RX:
				printf(" LIN_ID:0x%X\n", data_frame.ID);
				break;
			default:
				/**/
				break;
		}

		printf(" Data: ");
		for(i = 0U; i < data_frame.data_len; i++)
		{
			printf("%02x ", data_frame.Data[i]);
		}
		printf("\n");
	}
}

int32_t ipc_open0(void)
{
	int32_t ret = 0;
	uint32_t mode = IPC_MODE_0_MBOX;
	char readBuf[512] = {0};
	struct pollfd fds[1];
	int timeout = -1;
	ssize_t read_size;
	int ipc_read_packet_size = 512;
	int loop = 1;
	uint16_t cmd1;
	uint16_t cmd2;
	uint16_t length;

	fd0 = open(AXON_IPC_CM0_FILE, O_RDWR);

	if(fd0 < 0) {
		ERROR_LIBIPC_PRINTF("open fail : %s\n", AXON_IPC_CM0_FILE);
        return -1;
    } else {
    	printf("open succeeded, fd0: %d\n", fd0);
	}

	if (ioctl(fd0, IOCTL_IPC_SET_MODE, &mode) < 0) {
        perror("ioctl failed\n");
        close(fd0);
        return -1;
    }

#if 1
	fds[0].fd = fd0;
	fds[0].events = POLLIN;

	while (1) {
		printf("Waiting for data...\n");
        int poll_ret = poll(fds, 1, timeout);

        if (poll_ret == -1) {
            perror("Poll failed");
            break;
        } else if (poll_ret > 0) {
            if (fds[0].revents & POLLIN) {
				if(loop == 5) break;
                read_size = read(fd0, readBuf, sizeof(readBuf));

                if (read_size > 0) {
                    printf("Read %d bytes from device:\n", read_size);
                    for (int i = 0; i < read_size; i++) {
                        printf("lpa row data 0x%x\n ", readBuf[i]);
                    }
                    cmd1 = ((uint16_t)readBuf[3]<<8)||((uint16_t)readBuf[4]);
                    cmd2 = ((uint16_t)readBuf[5]<<8)||((uint16_t)readBuf[6]);
                    printf("cmd1: 0x%x,cmd2: 0x%x\n",cmd1,cmd2);
					loop++;
                } else if (read_size == 0) {
                    printf("Device closed\n");
                    close(fd0);
                    return 0;
                } else {
                    perror("Failed to read from device");
                }
            }
        }
	}
#endif

	return fd0;
}

int32_t ipc_open1(void)
{
	int32_t ret = 0;
	uint32_t mode = IPC_MODE_0_MBOX;
	char readBuf[512] = {0};
	struct pollfd fds[1];
	int timeout = -1;
	ssize_t read_size;
	int ipc_read_packet_size = 512;

	fd1 = open(AXON_IPC_CM1_FILE, O_RDWR|O_NONBLOCK);

	if(fd1 < 0)
    {
		ERROR_LIBIPC_PRINTF("open fail : %s\n", AXON_IPC_CM1_FILE);
        return -1;
    } else {
    	printf("open succeeded, fd1: %d\n", fd1);
	}

	if (ioctl(fd1, IOCTL_IPC_SET_MODE, &mode) < 0) {
        perror("ioctl failed\n");
        close(fd1);
        return -1;
    }

#if 1
	fds[0].fd = fd1;
	fds[0].events = POLLIN;

	while (1) {
		printf("Waiting for data...\n");
        int poll_ret = poll(fds, 1, timeout);

        if (poll_ret == -1) {
            perror("Poll failed");
            break;
        } else if (poll_ret > 0) {
            printf("poll_ret > 0\n");
			if (fds[0].revents & POLLIN) {
                read_size = read(fd1, readBuf, sizeof(readBuf));
                
				if (read_size > 0) {
                    printf("Read %zd bytes from device:\n", read_size);
                    for (int i = 0; i < read_size; i++) {
                        printf("0x%x ", readBuf[i]);
                    }
                    printf("\n");
                } else if (read_size == 0) {
                    printf("Device closed\n");
                    close(fd1);
                    return 0;
                } else {
                    perror("Failed to read from device");
                }
            }
        }
	}
#endif

	return fd1;
}

int32_t ipc_open2(void)
{
	int32_t ret = 0;
	uint32_t mode = IPC_MODE_0_MBOX;
	char readBuf[512] = {0};
	struct pollfd fds[1];
	int timeout = -1;
	ssize_t read_size;
	int ipc_read_packet_size = 512;

	fd2 = open(AXON_IPC_CM2_FILE, O_RDWR);

	if(fd2 < 0)
    {
		ERROR_LIBIPC_PRINTF("open fail : %s\n", AXON_IPC_CM2_FILE);
        return -1;
    } else {
    	printf("open succeeded, fd2: %d\n", fd2);
	}

	if (ioctl(fd2, IOCTL_IPC_SET_MODE, &mode) < 0) {
        perror("ioctl failed\n");
        close(fd2);
        return -1;
    }

#if 0
	fds[0].fd = fd2;
	fds[0].events = POLLIN;

	while (1) {
		printf("Waiting for data...\n");
        int poll_ret = poll(fds, 1, timeout);

        if (poll_ret == -1) {
            perror("Poll failed");
            break;
        } else if (poll_ret > 0) {
            if (fds[0].revents & POLLIN) {
                read_size = read(fd2, readBuf, sizeof(readBuf));
                if (read_size > 0) {
                    printf("Read %zd bytes from device:\n", read_size);
                    /*for (int i = 0; i < read_size; i++) {
                        printf("0x%x ", readBuf[i]);
                    }*/
                    printf("\n");
                } else if (read_size == 0) {
                    printf("Device closed\n");
                    close(fd2);
                    return 0;
                } else {
                    perror("Failed to read from device");
                }
            }
        }
	}
#endif

	return fd2;
}

int32_t ipc_open3(void)
{
	int32_t ret = 0;
	uint32_t mode = IPC_MODE_0_MBOX;
	char readBuf[512] = {0};
	struct pollfd fds[1];
	int timeout = -1;
	ssize_t read_size;
	int ipc_read_packet_size = 512;

	fd3 = open(AXON_IPC_CMN_FILE, O_RDWR);

	if(fd3 < 0)
    {
		ERROR_LIBIPC_PRINTF("open fail : %s\n", AXON_IPC_CMN_FILE);
        return -1;
    } else {
    	printf("open succeeded, fd3: %d\n", fd3);
	}

	if (ioctl(fd3, IOCTL_IPC_SET_MODE, &mode) < 0) {
        perror("ioctl failed\n");
        close(fd3);
        return -1;
    }

	return fd3;
}

int32_t ipc_oprd3(void)
{
	int32_t ret = 0;
	uint32_t mode = IPC_MODE_0_MBOX;
	char readBuf[512] = {0};
	struct pollfd fds[1];
	int timeout = -1;
	ssize_t read_size;
	int ipc_read_packet_size = 512;

	uint16_t cmd1;
	uint16_t cmd2;
	uint16_t IPC_datalen;
	uint8_t IPC_data[132];

	fd3 = open(AXON_IPC_CMN_FILE, O_RDWR|O_NONBLOCK);

	if(fd3 < 0)
    {
		ERROR_LIBIPC_PRINTF("open fail : %s\n", AXON_IPC_CMN_FILE);
        return -1;
    } else {
    	printf("open succeeded, fd3: %d\n", fd3);
	}

	if (ioctl(fd3, IOCTL_IPC_SET_MODE, &mode) < 0) {
        perror("ioctl failed\n");
        close(fd3);
        return -1;
    }

#if 1
	fds[0].fd = fd3;
	fds[0].events = POLLIN;

	while (1) {
		printf("Waiting for data...\n");
        int poll_ret = poll(fds, 1, timeout);

        if (poll_ret == -1) {
            perror("Poll failed");
            break;
        } else if (poll_ret > 0) {
            if (fds[0].revents & POLLIN) {
                read_size = read(fd3, readBuf, sizeof(readBuf));
                printf("read size : %d\n", read_size);
                if (read_size > 0) {
                    //printf("Read %d bytes from device:\n", read_size);
                    for (int i = 0; i < read_size; i++) {
                        printf("lpa row data[%d] 0x%x\n ",i, readBuf[i]);
                    }
                    /**** read data parse **********/
                    cmd1 = ((uint16_t)readBuf[3]<<8)|((uint16_t)readBuf[4]);
                    cmd2 = ((uint16_t)readBuf[5]<<8)|((uint16_t)readBuf[6]);
                    IPC_datalen = ((uint16_t)readBuf[7]<<8)|((uint16_t)readBuf[8]);
                    printf("cmd1: 0x%x,cmd2: 0x%x, length: 0x%x\n",cmd1,cmd2,IPC_datalen);
                    if((cmd1 == TCC_IPC_CMD_AP_TEST)&&(cmd2 == TCC_IPC_CMD_AP_SEND))
                    {
                    	for(int j=0; j<IPC_datalen; j++)
                    	{
							IPC_data[j] = readBuf[j+9];
							printf("lpc data[%d] 0x%x\n ",j, IPC_data[j]);
						}

						parse_data_frame(IPC_data, IPC_datalen);
                    }
                    break;
                } else if (read_size == 0) {
                    printf("Device closed\n");
                    close(fd3);
                    return 0;
                } else {
                    perror("Failed to read from device");
                }
            }
        }
	}
#endif

	return fd3;
}

int32_t ipc_setparam0(uint32_t vMin, uint32_t vTime)
{
	int32_t ret = -1;

	if(fd0 > -1)
	{
		axon_ipc_ctrl_param ipc_param;
		ipc_param.vMin = vMin;
		ipc_param.vTime = vTime;
		ret = ioctl(fd0, IOCTL_IPC_SET_PARAM , &ipc_param);
	}
	return ret;
}

int32_t ipc_setparam1(uint32_t vMin, uint32_t vTime)
{
	int32_t ret = -1;

	if(fd1 > -1)
	{
		axon_ipc_ctrl_param ipc_param;
		ipc_param.vMin = vMin;
		ipc_param.vTime = vTime;
		ret = ioctl(fd1, IOCTL_IPC_SET_PARAM , &ipc_param);
	}
	return ret;
}

int32_t ipc_setparam2(uint32_t vMin, uint32_t vTime)
{
	int32_t ret = -1;

	if(fd2 > -1)
	{
		axon_ipc_ctrl_param ipc_param;
		ipc_param.vMin = vMin;
		ipc_param.vTime = vTime;
		ret = ioctl(fd2, IOCTL_IPC_SET_PARAM , &ipc_param);
	}
	return ret;
}

int32_t ipc_setparam3(uint32_t vMin, uint32_t vTime)
{
	int32_t ret = -1;

	if(fd3 > -1)
	{
		axon_ipc_ctrl_param ipc_param;
		ipc_param.vMin = vMin;
		ipc_param.vTime = vTime;
		ret = ioctl(fd3, IOCTL_IPC_SET_PARAM , &ipc_param);
	}
	return ret;
}

int32_t ipc_getparam0()
{
	int32_t ret = -1;
	axon_ipc_ctrl_param ipc_param;

	if(fd0 > -1)
	{
		ret = ioctl(fd0, IOCTL_IPC_GET_PARAM , &ipc_param);
	}
	return ret;
}

int32_t ipc_getparam1()
{
	int32_t ret = -1;
	axon_ipc_ctrl_param ipc_param;

	if(fd1 > -1)
	{
		ret = ioctl(fd1, IOCTL_IPC_GET_PARAM , &ipc_param);
	}
	return ret;
}

int32_t ipc_getparam2()
{
	int32_t ret = -1;
	axon_ipc_ctrl_param ipc_param;

	if(fd2 > -1)
	{
		ret = ioctl(fd2, IOCTL_IPC_GET_PARAM , &ipc_param);
	}
	return ret;
}

int32_t ipc_getparam3()
{
	int32_t ret = -1;
	axon_ipc_ctrl_param ipc_param;

	if(fd3 > -1)
	{
		ret = ioctl(fd3, IOCTL_IPC_GET_PARAM , &ipc_param);
	}
	return ret;
}

int32_t ipc_write0(char *wbuffer, size_t wSize)
{
	int32_t ret =-1;
	int32_t i = 0;

	if((fd0 > -1)&&(wbuffer != NULL)&&(wSize > (size_t)0))
	{
		ret = write(fd0, wbuffer, wSize);
		/*for(i=0; i<wSize; i++) {
			printf("writeBuf[%d]: 0x%lx\n", i, wbuffer[i]);
		}*/
		if(ret < 0) {
			perror("write failed");
		}
	} else {
        if(fd0 <= -1) {
            printf("Invalid file descriptor: %d\n", fd0);
        }
        if(wbuffer == NULL) {
            printf("Invalid write buffer\n");
        }
        if(wSize <= (size_t)0) {
            printf("Invalid write size: %zu\n", wSize);
        }
    }

	return ret;
}

int32_t ipc_write1(char *wbuffer, size_t wSize)
{
	int32_t ret =-1;
	int32_t i = 0;

	if((fd1 > -1)&&(wbuffer != NULL)&&(wSize > (size_t)0))
	{
		ret = write(fd1, wbuffer, wSize);
		/*for(i=0; i<wSize; i++) {
			printf("writeBuf[%d]: 0x%lx\n", i, wbuffer[i]);
		}*/
		if(ret < 0) {
			perror("write failed");
		}
	} else {
        if(fd1 <= -1) {
            printf("Invalid file descriptor: %d\n", fd1);
        }
        if(wbuffer == NULL) {
            printf("Invalid write buffer\n");
        }
        if(wSize <= (size_t)0) {
            printf("Invalid write size: %zu\n", wSize);
        }
    }

	return ret;
}

int32_t ipc_write2(char *wbuffer, size_t wSize)
{
	int32_t ret =-1;
	int32_t i = 0;

	if((fd2 > -1)&&(wbuffer != NULL)&&(wSize > (size_t)0))
	{
		ret = write(fd2, wbuffer, wSize);
		/*for(i=0; i<wSize; i++) {
			printf("writeBuf[%d]: 0x%lx\n", i, wbuffer[i]);
		}*/
		if(ret < 0) {
			perror("write failed");
		}
	} else {
        if(fd2 <= -1) {
            printf("Invalid file descriptor: %d\n", fd2);
        }
        if(wbuffer == NULL) {
            printf("Invalid write buffer\n");
        }
        if(wSize <= (size_t)0) {
            printf("Invalid write size: %zu\n", wSize);
        }
    }

	return ret;
}

int32_t ipc_write3(char *wbuffer, size_t wSize)
{
	int32_t ret =-1;

	if((fd3 > -1)&&(wbuffer != NULL)&&(wSize > (size_t)0))
	{
		ret = write(fd3, wbuffer, wSize);
		/*for(i=0; i<wSize; i++) {
			printf("writeBuf[%d]: 0x%lx\n", i, wbuffer[i]);
		}*/
		if(ret < 0) {
			perror("write failed");
		}
	} else {
        if(fd3 <= -1) {
            printf("Invalid file descriptor: %d\n", fd3);
        }
        if(wbuffer == NULL) {
            printf("Invalid write buffer\n");
        }
        if(wSize <= (size_t)0) {
            printf("Invalid write size: %zu\n", wSize);
        }
    }

	return ret;
}

int32_t ipc_read0(char *rbuffer, size_t rSize)
{
	int32_t ret =-1;
	if((fd0 > -1)&&(rbuffer != NULL)&&(rSize > (size_t)0))
	{
		ret = read(fd0, rbuffer, rSize);
	}
	return ret;
}

int32_t ipc_read1(char *rbuffer, size_t rSize)
{
	int32_t ret =-1;
	if((fd1 > -1)&&(rbuffer != NULL)&&(rSize > (size_t)0))
	{
		ret = read(fd1, rbuffer, rSize);
	}
	return ret;
}

int32_t ipc_read2(char *rbuffer, size_t rSize)
{
	int32_t ret =-1;
	if((fd2 > -1)&&(rbuffer != NULL)&&(rSize > (size_t)0))
	{
		ret = read(fd2, rbuffer, rSize);
	}
	return ret;
}

int32_t ipc_read3(char *rbuffer, size_t rSize)
{
	int32_t ret =-1;
	if((fd3 > -1)&&(rbuffer != NULL)&&(rSize > (size_t)0))
	{
		ret = read(fd3, rbuffer, rSize);
	}
	return ret;
}

int32_t ipc_flush0(void)
{
	int32_t ret =-1;
	if(fd0 > -1)
	{
		ret = ioctl(fd0, IOCTL_IPC_FLUSH, NULL);
	}
	return ret;
}

int32_t ipc_flush1(void)
{
	int32_t ret =-1;
	if(fd1 > -1)
	{
		ret = ioctl(fd1, IOCTL_IPC_FLUSH, NULL);
	}
	return ret;
}

int32_t ipc_flush2(void)
{
	int32_t ret =-1;
	if(fd2 > -1)
	{
		ret = ioctl(fd2, IOCTL_IPC_FLUSH, NULL);
	}
	return ret;
}

int32_t ipc_flush3(void)
{
	int32_t ret =-1;
	if(fd3 > -1)
	{
		ret = ioctl(fd3, IOCTL_IPC_FLUSH, NULL);
	}
	return ret;
}

static int32_t ipc_ping_test0(axon_ipc_ping_info *pingInfo)
{
	int32_t ret =-1;
	if(fd0 > -1)
	{
		ret = ioctl(fd0, IOCTL_IPC_PING_TEST, &pingInfo);
	}
	(void)printf("\n[INFO] pingResult status\n");
	(void)printf("0: Ping success\n");
	(void)printf("1: [sender] ipc initialize failed\n");
	(void)printf("2: Other IPC not open\n");
	(void)printf("3: [sender] mbox is not set or error\n");
	(void)printf("4: [Receiver] mbox is not set or error\n");
	(void)printf("5: Can not send data. Maybe receiver mbox interrupt is busy\n");
	(void)printf("6,7: [Receiver] does not send respond data\n");
	return ret;
}

static int32_t ipc_ping_test1(axon_ipc_ping_info *pingInfo)
{
	int32_t ret =-1;
	if(fd1 > -1)
	{
		ret = ioctl(fd1, IOCTL_IPC_PING_TEST, &pingInfo);
	}
	(void)printf("\n[INFO] pingResult status\n");
	(void)printf("0: Ping success\n");
	(void)printf("1: [sender] ipc initialize failed\n");
	(void)printf("2: Other IPC not open\n");
	(void)printf("3: [sender] mbox is not set or error\n");
	(void)printf("4: [Receiver] mbox is not set or error\n");
	(void)printf("5: Can not send data. Maybe receiver mbox interrupt is busy\n");
	(void)printf("6,7: [Receiver] does not send respond data\n");
	return ret;
}

static int32_t ipc_ping_test2(axon_ipc_ping_info *pingInfo)
{
	int32_t ret =-1;
	if(fd2 > -1)
	{
		ret = ioctl(fd2, IOCTL_IPC_PING_TEST, &pingInfo);
	}
	(void)printf("\n[INFO] pingResult status\n");
	(void)printf("0: Ping success\n");
	(void)printf("1: [sender] ipc initialize failed\n");
	(void)printf("2: Other IPC not open\n");
	(void)printf("3: [sender] mbox is not set or error\n");
	(void)printf("4: [Receiver] mbox is not set or error\n");
	(void)printf("5: Can not send data. Maybe receiver mbox interrupt is busy\n");
	(void)printf("6,7: [Receiver] does not send respond data\n");
	return ret;
}

static int32_t ipc_ping_test3(axon_ipc_ping_info *pingInfo)
{
	int32_t ret =-1;
	if(fd3 > -1)
	{
		ret = ioctl(fd3, IOCTL_IPC_PING_TEST, &pingInfo);
	}
	(void)printf("\n[INFO] pingResult status\n");
	(void)printf("0: Ping success\n");
	(void)printf("1: [sender] ipc initialize failed\n");
	(void)printf("2: Other IPC not open\n");
	(void)printf("3: [sender] mbox is not set or error\n");
	(void)printf("4: [Receiver] mbox is not set or error\n");
	(void)printf("5: Can not send data. Maybe receiver mbox interrupt is busy\n");
	(void)printf("6,7: [Receiver] does not send respond data\n");
	return ret;
}

uint32_t ipc_status0(void)
{
	uint32_t status=0;

	if(fd0 > -1)
	{
		(void)ioctl(fd0, IOCTL_IPC_ISREADY, &status);
	}

	return status;
}

uint32_t ipc_status1(void)
{
	uint32_t status=0;

	if(fd1 > -1)
	{
		(void)ioctl(fd1, IOCTL_IPC_ISREADY, &status);
	}

	return status;
}

uint32_t ipc_status2(void)
{
	uint32_t status=0;

	if(fd2 > -1)
	{
		(void)ioctl(fd2, IOCTL_IPC_ISREADY, &status);
	}

	return status;
}

uint32_t ipc_status3(void)
{
	uint32_t status=0;

	if(fd3 > -1)
	{
		(void)ioctl(fd3, IOCTL_IPC_ISREADY, &status);
	}

	return status;
}

int32_t ipc_close0(void)
{
	int32_t ret;
	ret = close(fd0);

	if(ret != 0) {
		ERROR_LIBIPC_PRINTF("close fail\n");
	}

	return ret;
}

int32_t ipc_close1(void)
{
	int32_t ret;
	ret = close(fd1);

	if(ret != 0) {
		ERROR_LIBIPC_PRINTF("close fail\n");
	}

	return ret;
}

int32_t ipc_close2(void)
{
	int32_t ret;
	ret = close(fd2);

	if(ret != 0) {
		ERROR_LIBIPC_PRINTF("close fail\n");
	}

	return ret;
}

int32_t ipc_close3(void)
{
	int32_t ret;
	ret = close(fd3);

	if(ret != 0) {
		ERROR_LIBIPC_PRINTF("close fail\n");
	}

	return ret;
}

int IPC_CalcCrc16(const char *pucBuffer, int32_t uiLength, int uiInit)
{
    int32_t i;
    int temp;
    int crcCode;
    static const int crc16Table[256] =
    {
        0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
        0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
        0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
        0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
        0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
        0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
        0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
        0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
        0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
        0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
        0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
        0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
        0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
        0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
        0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
        0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
        0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
        0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
        0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
        0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
        0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
        0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
        0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
        0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
        0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
        0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
        0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
        0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
        0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
        0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
        0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
        0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0
    };

    crcCode = uiInit;

    if (pucBuffer != NULL)
    {
        for (i = 0; i < uiLength; i++)
        {
            temp    = (((crcCode & (int) 0xFF00) >> (int) 8) ^ pucBuffer[i]) & ((int) 0x00FF);
            crcCode = (crc16Table[temp] ^ ((crcCode & (int) 0x00FF) << (int) 8)) & ((int) 0xFFFF);
        }
    }

    return crcCode;
}

int ipc_make_packet(char *wbuffer, char add_num, int ipcCmd1, int ipcCmd2, int data_length)
{
	int32_t i = 0;
	int	crc = 0;
	int	packet_size = data_length + 11;

	if(wbuffer != NULL)
	{
		wbuffer[0] = 0xFF;
		wbuffer[1] = 0x55;
		wbuffer[2] = 0xAA;

		wbuffer[3] = (char) ((ipcCmd1 & (int) 0xFF00) >> (int) 8);
		wbuffer[4] = (char) (ipcCmd1 & (int) 0x00FF);
		wbuffer[5] = (char) ((ipcCmd2 & (int) 0xFF00) >> (int) 8);
		wbuffer[6] = (char) (ipcCmd2 & (int) 0x00FF);
		wbuffer[7] = (char) ((data_length & (int) 0xFF00) >> (int) 8);
		wbuffer[8] = (char) (data_length & (int) 0x00FF);

		for(i = 9; i < packet_size - 2; i++) {
			wbuffer[i] = add_num + 1;
		}

		crc = IPC_CalcCrc16(&wbuffer[0], (packet_size - 2U), 0);

		wbuffer[i++] = (char) ((crc & (int) 0xFF00) >> (int) 8);
		wbuffer[i] = (char) (crc & (int) 0x00FF);
	}

	return packet_size;
}

int ipc_Lpa_packet(char *wbuffer, char *ipc_buff, int ipcCmd1, int ipcCmd2, int data_length)
{
	int32_t i = 0;
	int	crc = 0;
	int	packet_size = data_length + 11;

	if(wbuffer != NULL)
	{
		wbuffer[0] = 0xFF;
		wbuffer[1] = 0x55;
		wbuffer[2] = 0xAA;

		wbuffer[3] = (char) ((ipcCmd1 & (int) 0xFF00) >> (int) 8);
		wbuffer[4] = (char) (ipcCmd1 & (int) 0x00FF);
		wbuffer[5] = (char) ((ipcCmd2 & (int) 0xFF00) >> (int) 8);
		wbuffer[6] = (char) (ipcCmd2 & (int) 0x00FF);
		wbuffer[7] = (char) ((data_length & (int) 0xFF00) >> (int) 8);
		wbuffer[8] = (char) (data_length & (int) 0x00FF);

		for(i = 9; i < packet_size - 2; i++) {
			wbuffer[i] = ipc_buff[i-9];
		}

		crc = IPC_CalcCrc16(&wbuffer[0], (packet_size - 2U), 0);

		wbuffer[i++] = (char) ((crc & (int) 0xFF00) >> (int) 8);
		wbuffer[i] = (char) (crc & (int) 0x00FF);
	}

	return packet_size;
}


void build_CANHeader(uint8_t *header_buffer, uint8_t Timestamp_onoff, uint32_t uCAN_ID, uint8_t uFDF, uint8_t uIDE, uint8_t uBRS)
{
    uint64_t can_header_frame = 0u;

    if(uIDE == 1U) // Extended ID
    {
        if(uFDF == 1U) // CAN FD
        {
            can_header_frame = TIMESTAMP(Timestamp_onoff) + PROTOCOL(0U) + CANEXTID(uCAN_ID) + FDF(1U) + RTR(0U) + IDE(1U) + BRS(uBRS);
        }
        else // classic CAN
        {
            can_header_frame = TIMESTAMP(Timestamp_onoff) + PROTOCOL(0U) + CANEXTID(uCAN_ID) + FDF(0U) + RTR(0U) + IDE(1U) + BRS(0U);
        }
    }
    else // Standard ID
    {
        if(uFDF == 1U) // CAN FD
        {
            can_header_frame = TIMESTAMP(Timestamp_onoff) + PROTOCOL(0U) + CANID(uCAN_ID) + FDF(1U) + RTR(0U) + IDE(0U) + BRS(uBRS);
        }
        else // classic CAN
        {
            can_header_frame = TIMESTAMP(Timestamp_onoff) + PROTOCOL(0U) + CANID(uCAN_ID) + FDF(0U) + RTR(0U) + IDE(0U) + BRS(0U);
        }
    }

    header_buffer[0] = (uint8_t)((can_header_frame&0x00000000FFULL));
    header_buffer[1] = (uint8_t)((can_header_frame&0x000000FF00ULL)>>8U);
    header_buffer[2] = (uint8_t)((can_header_frame&0x0000FF0000ULL)>>16U);
    header_buffer[3] = (uint8_t)((can_header_frame&0x00FF000000ULL)>>24U);
    header_buffer[4] = (uint8_t)((can_header_frame&0xFF00000000ULL)>>32U);

}


void LPA_msg(uint8_t protocol, uint8_t port, uint32_t id, uint8_t ext_opMode, uint8_t data_len, uint8_t *pData)
{

	if ((pData != NULL) && ( data_len <= 8U))
	{
        if(protocol == PROTOCOL_CAN)
        {
            build_CANHeader(&CetracSend[0], TIMESTAMP_ON, (uint32_t)id, 0U, ext_opMode, 0U);
        }
        else
        {
        	/**/
        }
		memcpy(&CetracSend[LPA_TX_HDR_SIZE], pData, data_len);

	}
}


static int ipc_commands(const char *cmd)
{
	int loop = 1;
	char *setVmin[AXON_STR_SIZE];
	char *setVtime[AXON_STR_SIZE];
	int vMin, vTime = 0;

	char i = 0;
	int ipc_packet_size = 0;
	int ipc_cmd1 = 0x01;
	int ipc_cmd2 = 0x01;
	int ipc_data_length = 501;
	int send_num = 5;

	int ipc_read_packet_size = 512;
	int read_size0 = 0;
	int read_size1 = 0;
	int read_size2 = 0;
	int read_size3 = 0;

	uint8_t DataLen;
	uint8_t IPCLen;
	uint8_t portN;
	uint32_t CanID;
	uint8_t Data[64];

	char str[128];
	char CMD;

    if(!strncmp(cmd, "o0", 3)) {
        (void)printf("\n ipc_cm7-0_open \n");
	    (void)ipc_open0();
    }
	else if(!strncmp(cmd, "o1", 3)) {
        (void)printf("\n ipc_cm7-1_open \n");
	    (void)ipc_open1();
    }
	else if(!strncmp(cmd, "o2", 3)) {
        (void)printf("\n ipc_cm7-2_open \n");
	    (void)ipc_open2();
    }
	else if(!strncmp(cmd, "o3", 3)) {
        (void)printf("\n ipc_cm7-np_open \n");
	    (void)ipc_open3();
    }
    else if(!strncmp(cmd, "or3", 4)) {
        (void)printf("\n ipc_cm7-np_open \n");
	    (void)ipc_oprd3();
    }
	else if(!strncmp(cmd, "sp", 3)) {
		(void)printf("\n Input set vTime (ex. Set 50->5(s) : ");
		fgets(setVtime, AXON_STR_SIZE, stdin);
		vTime = atoi(setVtime);

		(void)printf("\n Input set vMin : ");
		fgets(setVmin, AXON_STR_SIZE, stdin);
		vMin = atoi(setVmin);

        (void)ipc_setparam0(vMin, vTime);
		(void)ipc_setparam1(vMin, vTime);
		(void)ipc_setparam2(vMin, vTime);
		(void)ipc_setparam3(vMin, vTime);
    }
	else if(!strncmp(cmd, "gp", 3)) {
        (void)ipc_getparam0();
		(void)ipc_getparam1();
		(void)ipc_getparam2();
		(void)ipc_getparam3();
    }

	else if(!strncmp(cmd, "wr", 3)) {
		for (i = 0; i < send_num; i++)
		{
			ipc_packet_size = ipc_make_packet(&writeBuf, i, ipc_cmd1, ipc_cmd2, ipc_data_length);
	        (void)ipc_write0(&writeBuf, ipc_packet_size);
			(void)ipc_write1(&writeBuf, ipc_packet_size);
			(void)ipc_write2(&writeBuf, ipc_packet_size);
			(void)ipc_write3(&writeBuf, ipc_packet_size);
		}
    }

	else if(!strncmp(cmd, "wr0", 3)) {
		for (i = 0; i < send_num; i++)
		{
			ipc_packet_size = ipc_make_packet(writeBuf, i, ipc_cmd1, ipc_cmd2, ipc_data_length);
	        (void)ipc_write0(writeBuf, ipc_packet_size);
		}
    }
	else if(!strncmp(cmd, "wr1", 3)) {
		for (i = 0; i < send_num; i++)
		{
			ipc_packet_size = ipc_make_packet(&writeBuf, i, ipc_cmd1, ipc_cmd2, ipc_data_length);
	        (void)ipc_write1(&writeBuf, ipc_packet_size);
		}
    }

	else if(!strncmp(cmd, "wr2", 3)) {
		for (i = 0; i < send_num; i++)
		{
			ipc_packet_size = ipc_make_packet(&writeBuf, i, ipc_cmd1, ipc_cmd2, ipc_data_length);
	        (void)ipc_write2(&writeBuf, ipc_packet_size);
		}
    }
	else if(!strncmp(cmd, "wr3", 3)) {
		for (i = 0; i < send_num; i++)
		{
			ipc_packet_size = ipc_make_packet(writeBuf, i, ipc_cmd1, ipc_cmd2, ipc_data_length);
	        (void)ipc_write3(writeBuf, ipc_packet_size);
		}
    }
    else if(!strncmp(cmd, "can", 3)) {

		DataLen = 8;
		IPCLen = DataLen+LPA_TX_HDR_SIZE;
		for(i=0; i<DataLen; i++)
		{
			Data[i]= i;
		}

		memset(str, 0, sizeof(str));

		printf("CAN channel : 1 ~ 16 \n");
		fgets(str , 128, stdin);
		(void)sscanf(str,"%d",&portN);

		printf("CAN ID : 1 ~ 7ff \n");
		fgets(str , 128, stdin);
		(void)sscanf(str,"%x",&CanID);

		printf("port Number :%d, CAN ID : 0x%x, Data length : %d\n", portN, CanID, DataLen);
		(void)LPA_msg(PROTOCOL_CAN, portN, CanID, 0, (uint8_t)DataLen, Data);

		for(i=0; i<IPCLen; i++)
		{
			printf("senddata[%d]:%d\n", i, CetracSend[i]);
		}

		ipc_packet_size = ipc_Lpa_packet(writeBuf, CetracSend, TCC_IPC_CMD_AP_TEST, portN, IPCLen);
//		(void)ipc_write3(writeBuf, ipc_packet_size);
		(void)ipc_write1(writeBuf, ipc_packet_size);

    }

	else if(!strncmp(cmd, "rd", 3)) {
		read_size0 = read(fd0, &readBuf0[0], ipc_read_packet_size);
		read_size1 = read(fd1, &readBuf1[0], ipc_read_packet_size);
		read_size2 = read(fd2, &readBuf2[0], ipc_read_packet_size);
		read_size3 = read(fd3, &readBuf3[0], ipc_read_packet_size);

		printf("read_size : %d\n",read_size0);

		printf("readBuf0\n");
		for(i=0; i<ipc_read_packet_size; i++) {
			printf("%d:[0x%x] ", i, readBuf0[i]);
		}
		printf("\n");

		printf("readBuf1\n");
		for(i=0; i<ipc_read_packet_size; i++) {
			printf("%d:[0x%x] ", i, readBuf1[i]);
		}
		printf("\n");

		printf("readBuf2\n");
		for(i=0; i<ipc_read_packet_size; i++) {
			printf("%d:[0x%x] ", i, readBuf2[i]);
		}
		printf("\n");

		printf("readBuf3\n");
		for(i=0; i<ipc_read_packet_size; i++) {
			printf("%d:[0x%x] ", i, readBuf3[i]);
		}
		printf("\n");
    }

	else if(!strncmp(cmd, "rd0", 3)) {
		read_size0 = read(fd0, &readBuf0[0], ipc_read_packet_size);

		printf("read_size : %d\n",read_size0);

		printf("readBuf0\n");
		for(i=0; i<ipc_read_packet_size; i++) {
			printf("%d:[0x%x] ", i, readBuf0[i]);
		}
    }

	else if(!strncmp(cmd, "rd1", 3)) {
		read_size1 = read(fd1, &readBuf1[0], ipc_read_packet_size);

		printf("read_size : %d, ipc_read_packet_size : %d\n",read_size1,ipc_read_packet_size);

		printf("readBuf1\n");

		if(read_size1 > 0)
		{
			
			for(i=0; i<read_size1; i++) {
			//			for(i=0; i<ipc_read_packet_size; i++) {
				printf("%d:[0x%x] ", i, readBuf1[i]);
			}
		}
		else
		{
			printf("readBuf1 is empty\n");
		}
		printf("\n");
    }

	else if(!strncmp(cmd, "rd2", 3)) {
		read_size2 = read(fd2, &readBuf2[0], ipc_read_packet_size);

		printf("read_size : %d\n",read_size2);

		printf("readBuf2\n");
		for(i=0; i<ipc_read_packet_size; i++) {
			printf("%d:[0x%x] ", i, readBuf2[i]);
		}
		printf("\n");
    }

	else if(!strncmp(cmd, "rd3", 3)) {
		read_size3 = read(fd3, &readBuf3[0], ipc_read_packet_size);

		printf("read_size : %d\n",read_size3);

		printf("readBuf3\n");
		for(i=0; i<ipc_read_packet_size; i++) {
			printf("%d:[0x%x] ", i, readBuf3[i]);
		}
		printf("\n");
    }

	else if(!strncmp(cmd, "fl", 3)) {
        (void)ipc_flush0();
		(void)ipc_flush1();
		(void)ipc_flush2();
		(void)ipc_flush3();
    }

	else if(!strncmp(cmd, "pt0", 3)) {
        (void)ipc_ping_test0(0);
    }

	else if(!strncmp(cmd, "pt1", 3)) {
        (void)ipc_ping_test1(0);
    }

	else if(!strncmp(cmd, "pt2", 3)) {
        (void)ipc_ping_test2(0);
    }

	else if(!strncmp(cmd, "pt3", 3)) {
        (void)ipc_ping_test3(0);
    }

	else if(!strncmp(cmd, "st", 3)) {
        (void)ipc_status0();
		(void)ipc_status1();
		(void)ipc_status2();
		(void)ipc_status3();
    }

	else if(!strncmp(cmd, "cl", 3)) {
        (void)printf("\n ipc_close \n");
	    (void)ipc_close0();
	    (void)ipc_close1();
	    (void)ipc_close2();
	    (void)ipc_close3();
    }

	else if(!strncmp(cmd, "z", 2)) {
    	loop = 0;
    }
    else if (!strncmp(cmd, "test", 5)) {
    	printf("\n Ap build test");
    }

	else {
        (void)printf("\n Command ERROR!! Enter the correct value. \n");
    }

    return loop;
}

int32_t main(int argc, char* argv[])
{
	(void)argc;
	(void)argv;
	int32_t ret = 0;
	int32_t loop = 1;

	char str[AXON_STR_SIZE];
	const char *fi;
	char cmd[10] = {0,};

	printf("ksh ipc test 9\n");

	while(loop) {
		if(!loop) break;

		(void)printf("\n\n\n\n\n\n\n\n=======================================\n");
        (void)printf("      IPC TEST       \n");
		(void)printf("NOTICE : When you open the new mailbox channel       \n");
		(void)printf("			please enter close!!!       \n");
        (void)printf("=======================================\n");

        (void)printf("set open : Enter o0 --> CM7-0\n");
		(void)printf("set open : Enter o1 --> CM7-1\n");
		(void)printf("set open : Enter o2 --> CM7-2\n");
		(void)printf("set open : Enter o3 --> CM7-np\n");
		(void)printf("set open && read : Enter or3 --> CM7-np\n");

        (void)printf("set param : Enter sp --> CM7-ALL\n");
		(void)printf("get param : Enter gp --> CM7-ALL\n");

        (void)printf("set write : Enter wr --> CM7-ALL\n");
		(void)printf("set write : Enter wr0 --> CM7-0\n");
		(void)printf("set write : Enter wr1 --> CM7-1\n");
		(void)printf("set write : Enter wr2 --> CM7-2\n");
		(void)printf("set write : Enter wr3 --> CM7-np\n");
		(void)printf("can write : Enter can --> CM7-np\n");

        (void)printf("set read : Enter rd --> CM7-ALL\n");
		(void)printf("set read : Enter rd0 --> CM7-0\n");
		(void)printf("set read : Enter rd1 --> CM7-1\n");
		(void)printf("set read : Enter rd2 --> CM7-2\n");
		(void)printf("set read : Enter rd3 --> CM7-np\n");

		(void)printf("set flush : Enter fl --> CM7-ALL\n");

		(void)printf("set ping_test : Enter pt0 --> CM7-0\n");
		(void)printf("set ping_test : Enter pt1 --> CM7-1\n");
		(void)printf("set ping_test : Enter pt2 --> CM7-2\n");
		(void)printf("set ping_test : Enter pt3 --> CM7-np\n");

		(void)printf("get status : Enter st --> CM7-ALL\n");

		(void)printf("set close : Enter cl --> CM7-ALL\n");

        (void)printf("finish this app : Enter z\n");
        (void)printf("=======================================\n");

		(void)memset(str, 0, sizeof(str));
		fi = fgets(str, AXON_STR_SIZE, stdin);
		if(fi != NULL) {
			(void)sscanf(str, "%10s", cmd);
			loop = ipc_commands(cmd);
		}
	}

	return ret;
}
