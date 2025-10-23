"""
統一されたエラーハンドリング

全APIエンドポイントで一貫したエラーレスポンス形式を提供します。
"""
from flask import jsonify
from logger import logger


def register_error_handlers(app):
    """Flaskアプリケーションにエラーハンドラーを登録"""

    @app.errorhandler(400)
    def bad_request(error):
        """400 Bad Request"""
        logger.warning(f"Bad Request: {str(error)}")
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description) if hasattr(error, 'description') else str(error),
            'status': 400
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """401 Unauthorized"""
        logger.warning(f"Unauthorized: {str(error)}")
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required',
            'status': 401
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        """403 Forbidden"""
        logger.warning(f"Forbidden: {str(error)}")
        return jsonify({
            'error': 'Forbidden',
            'message': 'Access denied',
            'status': 403
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        """404 Not Found"""
        logger.info(f"Not Found: {str(error)}")
        return jsonify({
            'error': 'Not Found',
            'message': str(error.description) if hasattr(error, 'description') else 'Resource not found',
            'status': 404
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        """405 Method Not Allowed"""
        logger.warning(f"Method Not Allowed: {str(error)}")
        return jsonify({
            'error': 'Method Not Allowed',
            'message': str(error.description) if hasattr(error, 'description') else str(error),
            'status': 405
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        """500 Internal Server Error"""
        logger.error(f"Internal Server Error: {str(error)}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred. Please try again later.',
            'status': 500
        }), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        """503 Service Unavailable"""
        logger.error(f"Service Unavailable: {str(error)}")
        return jsonify({
            'error': 'Service Unavailable',
            'message': 'The service is temporarily unavailable. Please try again later.',
            'status': 503
        }), 503

    logger.info("Error handlers registered successfully")
