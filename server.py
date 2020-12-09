from waitress import serve
import app
import logging
from paste.translogger import TransLogger

logger = logging.getLogger('waitress')
logger.setLevel(logging.DEBUG)
app.app.logger.setLevel(logging.DEBUG)

serve(TransLogger(app.app), host="0.0.0.0", port=7897)
