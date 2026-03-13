FROM nginx:alpine

# Remove the default Nginx configuration file
RUN rm /etc/nginx/conf.d/default.conf

# Copy your custom Nginx configuration file
COPY ./NginxFiles/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80