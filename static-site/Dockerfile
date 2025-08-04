FROM alpine:latest
RUN apk -U upgrade
RUN apk add --update --no-cache git git-lfs nginx npm

RUN git lfs install

EXPOSE 80
EXPOSE 443

# Cleanup
WORKDIR /root
RUN apk cache clean
RUN rm -rf /tmp/* /var/tmp/*

ENTRYPOINT ["nginx", "-g", "daemon off;"]