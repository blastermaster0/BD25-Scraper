from waitress import serve
import app
import logging

logger = logging.getLogger('waitress')
logger.setLevel(logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

serve(app.app, host="0.0.0.0", port=7897)
