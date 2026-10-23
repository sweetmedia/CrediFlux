"""Storage S3 de los estáticos (sólo producción con ``USE_S3``).

Los archivos de usuario son privados (``AWS_DEFAULT_ACL = 'private'``); los
estáticos se siguen publicando con lectura pública y URLs sin firma para que
``STATIC_URL`` y la caché funcionen.
"""
from storages.backends.s3boto3 import S3Boto3Storage


class PublicStaticS3Storage(S3Boto3Storage):
    default_acl = 'public-read'
    querystring_auth = False
