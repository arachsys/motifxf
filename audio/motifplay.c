#include <errno.h>
#include <netdb.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>

#define BUFFER 0x180000
#define CHUNK 0x8000
#define SERVICE "5556"

void die(const char *s) {
  perror(s);
  exit(EXIT_FAILURE);
}

int openstream(char *host, char *port) {
  struct addrinfo *a, *ai, hints;
  int sock, zero = 0;

  memset(&hints, 0, sizeof(hints));
  hints.ai_flags = AI_ADDRCONFIG;
  hints.ai_socktype = SOCK_STREAM;
  hints.ai_family = AF_UNSPEC;

  if (getaddrinfo(host, port, &hints, &ai) < 0 || !ai) {
    fprintf(stderr, "unknown host %s\n", host);
    exit(EXIT_FAILURE);
  }

  for (a = ai; a != NULL; a = a->ai_next) {
    sock = socket(a->ai_family, a->ai_socktype, a->ai_protocol);
    if (sock < 0)
      continue;
    if (setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &zero, sizeof(zero)) < 0)
      die("setsockopt SO_SNDBUF");
    if (connect(sock, a->ai_addr, a->ai_addrlen) == 0)
      break;
    close(sock);
  }

  if (!a)
    die("connect");

  freeaddrinfo(ai);
  return sock;
}

size_t readall(int fd, void *buf, size_t n) {
  ssize_t m, p;

  for (p = 0; p < n; p += m)
    if ((m = read(fd, buf + p, n - p)) <= 0) {
      if (errno != EAGAIN && errno != EINTR)
        break;
      m = 0;
    }
  return (size_t) p;
}

size_t writeall(int fd, void *buf, size_t n) {
  ssize_t m, p;

  for (p = 0; p < n; p += m)
    if ((m = write(fd, buf + p, n - p)) <= 0) {
      if (errno != EAGAIN && errno != EINTR)
        break;
      m = 0;
    }
  return (size_t) p;
}

void sigint_handler(int sig) {
  exit(EXIT_SUCCESS);
}

int main(int argc, char **argv) {
  unsigned char buf[CHUNK + 8];
  size_t n;
  struct sigaction sa;
  int sock;

  if (argc != 2) {
    fprintf(stderr, "\
Usage: %s MOTIF-HOSTNAME < AUDIO-FILE\n\
Connect to the specified Yamaha Motif synthesizer and play 44.1kHz stereo\n\
audio data in raw 16-bit signed little-endian format from stdin, finishing\n\
cleanly on EOF.\n\
", argv[0]);
    return EXIT_FAILURE;
  }

  sock = openstream(argv[1], SERVICE);

  sa.sa_flags = SA_RESETHAND | SA_RESTART;
  sa.sa_handler = sigint_handler;
  sigemptyset(&sa.sa_mask);
  sigaction(SIGINT, &sa, NULL);

  memcpy(buf, "WAVE\x00\x00\x00\x00", 8);
  while ((n = readall(0, buf + 8, sizeof(buf) - 8)) > 0) {
    buf[4] = n & 0xff;
    buf[5] = (n >> 8) & 0xff;
    if (writeall(sock, buf, n + 8) != n + 8)
      die("socket write");
  }

  memset(buf + 8, 0, sizeof(buf) - 8);
  buf[4] = (sizeof(buf) - 8) & 0xff;
  buf[5] = ((sizeof(buf) - 8) >> 8) & 0xff;
  for (n = 0; n < BUFFER; n += CHUNK)
    if (writeall(sock, buf, sizeof(buf)) != sizeof(buf))
      die("socket write");

  close(sock);
  return EXIT_SUCCESS;
}
