FROM alpine:latest
RUN apk -U upgrade
RUN apk add --update --no-cache nginx certbot certbot-nginx

RUN rm /etc/nginx/http.d/*

EXPOSE 80
EXPOSE 443

# Cleanup
WORKDIR /root
RUN apk cache clean
RUN rm -rf /tmp/* /var/tmp/*

ENTRYPOINT ["nginx", "-g", "daemon off;"]