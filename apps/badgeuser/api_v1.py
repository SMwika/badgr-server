# encoding: utf-8
from __future__ import unicode_literals

import csv
import aniso8601
import datetime

from django.http import HttpResponse

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions

from badgeuser.models import CachedEmailAddress, BadgeUser
from badgeuser.serializers_v1 import EmailSerializerV1
from apispec_drf.decorators import apispec_list_operation, apispec_post_operation, apispec_operation, \
    apispec_get_operation, apispec_delete_operation, apispec_put_operation


class BadgeUserEmailList(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @apispec_list_operation('BadgeUserEmail',
        summary="Get a list of user's registered emails",
        tags=['BadgeUsers']
    )
    def get(self, request, **kwargs):
        instances = request.user.cached_emails()
        serializer = EmailSerializerV1(instances, many=True, context={'request': request})
        return Response(serializer.data)

    @apispec_operation(
        summary="Register a new unverified email",
        tags=['BadgeUsers'],
        properties=[
            {
                'in': 'formData',
                'name': "email",
                'type': "string",
                'format': "email",
                'description': 'The email to register'
            }
        ]
    )
    def post(self, request, **kwargs):
        serializer = EmailSerializerV1(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        email_address = serializer.save(user=request.user)
        email = serializer.data
        email_address.send_confirmation(request)
        return Response(email, status=status.HTTP_201_CREATED)


class BadgeUserEmailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_email(self, **kwargs):
        try:
            email_address = CachedEmailAddress.cached.get(**kwargs)
        except CachedEmailAddress.DoesNotExist:
            return None
        else:
            return email_address

class BadgeUserEmailDetail(BadgeUserEmailView):
    model = CachedEmailAddress

    @apispec_get_operation('BadgeUserEmail',
        summary="Get detail for one registered email",
        tags=['BadgeUsers']
    )
    def get(self, request, id, **kwargs):
        email_address = self.get_email(pk=id)
        if email_address is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if email_address.user_id != self.request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = EmailSerializerV1(email_address, context={'request': request})
        return Response(serializer.data)

    @apispec_delete_operation('BadgeUserEmail',
        summary="Remove a registered email for the current user",
        tags=['BadgeUsers']
    )
    def delete(self, request, id, **kwargs):
        email_address = self.get_email(pk=id)
        if email_address is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if email_address.user_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if email_address.primary:
            return Response({'error': "Can not remove primary email address"}, status=status.HTTP_400_BAD_REQUEST)

        if self.request.user.emailaddress_set.count() == 1:
            return Response({'error': "Can not remove only email address"}, status=status.HTTP_400_BAD_REQUEST)

        email_address.delete()
        return Response(status.HTTP_200_OK)

    @apispec_put_operation('BadgeUserEmail',
        summary='Update a registered email for the current user',
        tags=['BadgeUsers']
    )
    def put(self, request, id, **kwargs):
        email_address = self.get_email(pk=id)
        if email_address is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if email_address.user_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if email_address.verified:
            if request.data.get('primary'):
                email_address.set_as_primary()
                email_address.publish()
        else:
            if request.data.get('resend'):
                email_address.send_confirmation(request=request)

        serializer = EmailSerializerV1(email_address, context={'request': request})
        serialized = serializer.data
        return Response(serialized, status=status.HTTP_200_OK)

'''
Helper that handles creating an HttpResponse containing a csv file
that cointains meta data on Badgr users who have opted in for
marketing.

@param datetime.date object
@return django.http.HttpResponse
'''
def get_marketing_opted_in_users_csv(date=None):
    opted_in_users = []
    if date == None:
        opted_in_users = BadgeUser.objects.filter(marketing_opt_in=True)
        date = "ALL"
    else:
        search_date = datetime.datetime.combine(date, datetime.datetime.min.time())
        search_date -= datetime.timedelta(days=1)
        opted_in_users = BadgeUser.objects.filter(marketing_opt_in=True, date_joined__gte=search_date)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="marketing_opted_in_users_%s.csv"' % date
    fieldnames = ['date', 'opt_in', 'email', 'first_name', 'last_name']
    writer = csv.DictWriter(response, fieldnames=fieldnames)

    writer.writeheader()
    for user in opted_in_users:
        date_joined = user.date_joined
        opt_in = "True"
        email = user.primary_email
        first_name = user.first_name
        last_name = user.last_name
        writer.writerow({'date': date_joined, 'opt_in': opt_in, 'email': email,
         'first_name': first_name, 'last_name': last_name})

    return response


'''
Returns an HTTP response to an HTTP request containing a csv file
that cointains meta data on Badgr users who have opted in for
marketing. Expects a '?date=DATE' query paremetr where DATE is
a string of the form 'YEAR-MONTH-DAY'
@param request rest_framework.request.Request
@return django.http.HttpResponse
'''
@api_view(['GET'])
@permission_classes((permissions.IsAuthenticated,))
def marketing_opted_in_users_csv_view(request, **kwargs):
    query_dict = request.GET
    date = None
    if 'date' in query_dict:
        date = query_dict['date']
        print("init query param")
        print(date)

        try:
            date = aniso8601.parse_date(date)
        except:
            return Response({'error': "Incorrect date format. Expected date to be in datetime.date format."}, status=status.HTTP_400_BAD_REQUEST)

    response = get_marketing_opted_in_users_csv(date=date)
    return response
