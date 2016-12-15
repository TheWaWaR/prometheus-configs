global:
  # The smarthost and SMTP sender used for mail notifications.
  %(smtp_smarthost)s
  %(smtp_from)s
  %(smtp_auth_username)s
  %(smtp_auth_password)s

# The directory from which notification templates are read.
templates: 

# The root route on which each incoming alert enters.
route:
  # The labels by which incoming alerts are grouped together. For example,
  # multiple alerts coming in for cluster=A and alertname=LatencyHigh would
  # be batched into a single group.
  # group_by: ['alertname', 'cluster', 'service']

  # When a new group of alerts is created by an incoming alert, wait at
  # least 'group_wait' to send the initial notification.
  # This way ensures that you get multiple alerts for the same group that start
  # firing shortly after another are batched together on the first 
  # notification.
  group_wait: 30s

  # When the first notification was sent, wait 'group_interval' to send a batch
  # of new alerts that started firing for that group.
  group_interval: 5m

  # If an alert has successfully been sent, wait 'repeat_interval' to
  # resend them.
  repeat_interval: 3h 

  # A default receiver
  receiver: webhook


receivers:
- name: 'mail-receiver'
  email_configs:
  - to: '%(email_to)s'
- name: 'webhook'
  webhook_configs:
  - url: 'http://xxX'
