#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr, "usage: %s <host> <port> <marker> <count> <interval_ms>\n", argv[0]);
        return 2;
    }

    const char *host = argv[1];
    int port = atoi(argv[2]);
    const char *marker = argv[3];
    int count = atoi(argv[4]);
    int interval_ms = atoi(argv[5]);
    if (port <= 0 || port > 65535 || count <= 0 || interval_ms < 0) {
        fprintf(stderr, "invalid port, count, or interval_ms\n");
        return 2;
    }

    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        perror("socket");
        return 1;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)port);
    if (inet_pton(AF_INET, host, &addr.sin_addr) != 1) {
        fprintf(stderr, "invalid IPv4 host: %s\n", host);
        close(fd);
        return 2;
    }

    for (int i = 0; i < count; i++) {
        char payload[256];
        int length = snprintf(payload, sizeof(payload), "%s|%04d\n", marker, i);
        if (length <= 0 || length >= (int)sizeof(payload)) {
            fprintf(stderr, "payload formatting failed\n");
            close(fd);
            return 1;
        }
        ssize_t sent = sendto(fd, payload, (size_t)length, 0, (struct sockaddr *)&addr, sizeof(addr));
        if (sent < 0) {
            perror("sendto");
            close(fd);
            return 1;
        }
        if (interval_ms > 0 && i + 1 < count) {
            usleep((useconds_t)interval_ms * 1000U);
        }
    }

    close(fd);
    return 0;
}
