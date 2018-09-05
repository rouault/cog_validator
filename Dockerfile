# Mostly derived from https://github.com/mojodna/marblecutter-tools/blob/master/aws/Dockerfile

FROM lambci/lambda:build-python2.7

ARG http_proxy

# Install deps

RUN \
  rpm --rebuilddb && \
  yum install -y \
    automake16 \
    libcurl-devel

RUN \
  # Build zstd
  curl -L https://github.com/facebook/zstd/archive/v1.3.3.tar.gz | tar zxf - -C /tmp \
  && cd /tmp/zstd-1.3.3/lib \
  && make -j3 PREFIX=/var/task ZSTD_LEGACY_SUPPORT=0 CFLAGS=-O1 \
  && make install PREFIX=/var/task ZSTD_LEGACY_SUPPORT=0 CFLAGS=-O1 \
  && cd /tmp \
  && rm -rf /tmp/zstd-1.3.3

# Fetch PROJ.4

RUN \
  curl -L http://download.osgeo.org/proj/proj-4.9.3.tar.gz | tar zxf - -C /tmp \
  && cd /tmp/proj-4.9.3 \
  && ./configure --prefix=/var/task \
  && make -j $(nproc) \
  && make install \
  && cd /tmp \
  && rm -rf /tmp/proj-4.9.3

# Fetch GDAL

RUN \
  mkdir -p /tmp/gdal \
  && curl -L http://download.osgeo.org/gdal/2.3.1/gdal-2.3.1.tar.gz | tar zxf - -C /tmp/gdal --strip-components=1 \
  && cd /tmp/gdal \
  && ./configure \
    --prefix=/var/task \
    --datarootdir=/var/task/share/gdal \
    --with-jpeg=internal \
    --without-qhull \
    --without-mrf \
    --without-grib \
    --without-pcraster \
    --without-png \
    --without-gif \
    --with-zstd=/var/task \
    --without-pcidsk \
  && make -j $(nproc) \
  && cd swig/python \
  && make \
  && cd ../.. \
  && make install

# Install Python deps in a virtualenv

RUN \
  virtualenv /tmp/virtualenv

ENV PATH /tmp/virtualenv/bin:/var/task/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /var/task

COPY requirements.txt /var/task/requirements.txt

RUN pip install -r requirements.txt

# Lambda stuff
# Add GDAL libs to the function zip
RUN \
  strip lib/libgdal.so.20.4.1 && \
  strip lib/libproj.so.12.0.0 && \
  strip lib/libzstd.so.1.3.3

RUN \
  zip --symlinks \
    -r /tmp/task.zip \
    lib/libgdal.so* \
    lib/libproj.so* \
    lib/libzstd.so* \
    share/gdal/
# Add Python deps to the function zip
RUN \
  cd /tmp/virtualenv/lib/python2.7/site-packages \
  && find . -name \*.so\* -exec strip {} \; \
  && zip  -r /tmp/task.zip flask werkzeug jinja2 markupsafe itsdangerous.py* click requests idna chardet certifi urllib3 osgeo \
  && cd /tmp/gdal/swig/python/build/lib.linux-x86_64-2.7 \
  && find . -name \*.so\* -exec strip {} \; \
  && zip -r /tmp/task.zip .

# Local execution
RUN pip install /tmp/gdal/swig/python

WORKDIR /tmp/virtualenv
COPY templates/ /tmp/virtualenv/templates/
COPY cog_validator.py /tmp/virtualenv/
COPY validate_cloud_optimized_geotiff.py /tmp/virtualenv/
ENV COG_LIMIT=50
ENV LISTEN=0.0.0.0
EXPOSE 5000
CMD ["/tmp/virtualenv/bin/python", "/tmp/virtualenv/cog_validator.py"]
