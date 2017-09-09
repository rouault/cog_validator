# Mostly derived from https://github.com/mojodna/marblecutter-tools/blob/master/aws/Dockerfile

FROM lambci/lambda:build-python2.7

ARG http_proxy

# Install deps

RUN \
  rpm --rebuilddb && \
  yum install -y \
    automake16 \
    libcurl-devel

# Fetch PROJ.4

RUN \
  curl -L http://download.osgeo.org/proj/proj-4.9.3.tar.gz | tar zxf - -C /tmp

# Build and install PROJ.4

WORKDIR /tmp/proj-4.9.3

RUN \
  ./configure \
    --prefix=/var/task && \
  make -j $(nproc) && \
  make install

# Fetch GDAL

RUN \
  mkdir -p /tmp/gdal && \
  curl -L http://download.osgeo.org/gdal/2.2.1/gdal-2.2.1.tar.gz | tar zxf - -C /tmp/gdal --strip-components=1

# Build + install GDAL

WORKDIR /tmp/gdal

RUN \
  ./configure \
    --prefix=/var/task \
    --datarootdir=/var/task/share/gdal \
    --with-jpeg=internal \
    --without-qhull \
    --without-mrf \
    --without-grib \
    --without-pcraster \
    --without-png \
    --without-gif \
    --without-pcidsk && \
  make -j $(nproc) && \
  cd swig/python && \
  make && \
  cd ../.. && \
  make install

# Install Python deps in a virtualenv

RUN \
  virtualenv /tmp/virtualenv

ENV PATH /tmp/virtualenv/bin:/var/task/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /var/task

COPY requirements.txt /var/task/requirements.txt

RUN pip install -r requirements.txt

# Add GDAL libs to the function zip

RUN \
  strip lib/libgdal.so.20.3.0 && \
  strip lib/libproj.so.12.0.0

RUN \
  zip --symlinks \
    -r /tmp/task.zip \
    lib/libgdal.so* \
    lib/libproj.so* \
    share/gdal/

# Add Python deps to the function zip

WORKDIR /tmp/virtualenv/lib/python2.7/site-packages

RUN find . -name \*.so\* -exec strip {} \;

RUN \
  zip  -r /tmp/task.zip flask werkzeug jinja2 markupsafe itsdangerous.py* click requests idna chardet certifi urllib3 osgeo

WORKDIR /tmp/gdal/swig/python/build/lib.linux-x86_64-2.7

RUN find . -name \*.so\* -exec strip {} \;

RUN zip -r /tmp/task.zip .
