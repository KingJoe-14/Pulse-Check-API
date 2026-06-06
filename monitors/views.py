from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from monitors.services.monitor_service import (
    register_monitor,
    get_monitor,
    get_all_monitors,
)


class MonitorListView(APIView):

    def get(self, request):
        """GET /monitors — list all monitors"""
        monitors = get_all_monitors()
        return Response(monitors, status=status.HTTP_200_OK)

    def post(self, request):
        """POST /monitors — register a new monitor"""
        data = request.data

        # Validate required fields
        required = ['id', 'timeout', 'alert_email']
        for field in required:
            if field not in data:
                return Response(
                    {'error': f'Missing required field: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        device_id   = data['id']
        timeout     = data['timeout']
        alert_email = data['alert_email']

        # Validate timeout is a positive integer
        if not isinstance(timeout, int) or timeout <= 0:
            return Response(
                {'error': 'timeout must be a positive integer (seconds)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        monitor, error = register_monitor(device_id, timeout, alert_email)

        if error:
            return Response(
                {'error': error},
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            {
                'message': f'Monitor for {device_id} created successfully',
                'monitor': monitor,
            },
            status=status.HTTP_201_CREATED
        )


class MonitorDetailView(APIView):

    def get(self, request, device_id):
        """GET /monitors/{id} — get a single monitor"""
        monitor = get_monitor(device_id)
        if not monitor:
            return Response(
                {'error': f'Monitor {device_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(monitor, status=status.HTTP_200_OK)
