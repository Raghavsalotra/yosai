"""
I'm unsure as to how long I will use pypubsub for inter-application event
messaging.  So, I'm creating a proxy, EventBus, between pypubsub and 
my application, allowing me to swap out the event bus implementation later 
without impacting my core application modules.  The core application modules
know WHAT needs to be communicated with the bus but now HOW (EventBus
knows HOW).
"""

from pubsub import pub

from pubsub.core import (
    ListenerMismatchError,
    SenderMissingReqdMsgDataError, 
    SenderUnknownMsgDataError,
    TopicDefnError,
    TopicNameError,
)

from yosai import (
    EventBusTopicException,
    EventBusMessageDataException,
    EventBusSubscriptionException,
    LogManager,
)

from .interfaces import (
    IEventBus,
)

import calendar
import time


class Event(object):
    """ 
    There is a standard structure for events communicated over the eventbus. 
    Yosai's Event design is a departure from Shiro's use of abstract and 
    hierarchical concrete Event classes, each of which essentially has
    the same characteristics and behavior.
    """

    def __init__(self, event_topic, event_type, source, **eventattrs):
        self.event_type = event_type  # ex:  AUTHENTICATION
        self.event_topic = event_topic  # ex:  AUTHENTICATION_FAILED
        self.source = source  # the object that emitted the event 
        self.timestamp = calendar.timegm(time.gmtime())  # UNIX timestamp
        self.__dict__.update(**eventattrs)  # DG:  risky?


class EventBus(IEventBus, object):
    """
    Yosai's EventBus is a proxy to pypubsub.  Its API is unique to Yosai,
    having little in common with the EventBus implementation in Shiro.

    Note:  most of the comments here are pasted from pypubsub's documentation
    """

    def __init__(self):
        self._event_bus = pub 

        # The following two settings enforce topic naming convention.
        # If you want to catch topic naming exceptions, Uncomment the settings 
        # and specify a source for the topic tree 
        # self._event_bus.setTopicUnspecifiedFatal(True)()
        # self._event_bus.addTopicDefnProvider( kwargs_topics, pub.TOPIC_TREE_FROM_CLASS )

    def is_registered(self, listener, topic_name):
        
        try:
            return self._event_bus.isSubscribed(listener, topic_name)
        except TopicNameError:
            msg = "TopicNameError: Unrecognized topic naming convention"
            # log here
            print(msg)
            raise EventBusTopicException(msg)
        except TopicDefnError:
            msg = "TopicDefnError: Unregistered topic name"
            # log here
            print(msg)
            raise EventBusTopicException(msg)

    def publish(self, topic_name, **kwargs):
        """ 
        Sends a message to the bus

        :param topic_name: name of message topic
        :type topic_name: dotted-string or tuple 
        :param kwargs: message data (must satisfy the topic’s MetadataService)
        """
        try:
            self._event_bus.sendMessage(topic_name, **kwargs) 
        except SenderMissingReqdMsgDataError:
            msg = "SenderMissingReqdMsgDataError: can't send message"
            # log here
            print(msg) 
            raise EventBusMessageDataException(msg)
        except SenderUnknownMsgDataError:
            msg = ("SenderUnknownMsgDataError: One of the keyword arguments "
                   "is not part of MDS")
            # log here
            print(msg)
            raise EventBusMessageDataException(msg)
        except TopicDefnError:
            msg = "TopicDefnError: Sending message to an unregistered topic name"
            # log here
            print(msg)
            raise EventBusTopicException(msg)
        return True

    def register(self, _callable, topic_name):
        """
        Subscribe listener to named topic. 
        
        Note that if 'subscribe' notification is on, the handler's
        'notifySubscribe' method is called after subscription.

        :raises ListenerMismatchError: if listener isn’t compatible with the
                                       topic’s MDS (Metadata Service). 
        :returns (pubsub.core.Listener, success): success is False if listener 
                                                  is already subscribed 

        """
        subscribed_listener = None
        success = None
        
        try:
            subscribed_listener, success =\
                self._event_bus.subscribe(_callable, topic_name)
        except ListenerMismatchError:
            msg = ("ListenerMismatchError: Invalid Listener -- callable does "
                   "not have a signature (call protocol) compatible with the "
                   "MDS of topic: {0}".format(topic_name))
            # log here
            print(msg)
            raise EventBusSubscriptionException(msg)
        except TopicDefnError:
            msg = "TopicDefnError: Unregistered topic name"
            # log here
            print(msg)
            raise EventBusTopicException(msg)
        else:  # return only if no exception raised
            return subscribed_listener, success

    def unregister(self, listener, topic_name):
        try:
            unsubscribed_listener = self._event_bus.unsubscribe(
                listener, topic_name)
        except TopicNameError:
            msg = "TopicNameError: Unrecognized eventbus topic naming convention"
            # log here
            print(msg)
            raise EventBusTopicException(msg)
        except TopicDefnError:
            msg = "TopicDefnError: Unregistered topic name"
            # log here
            print(msg)
            raise EventBusTopicException(msg)
        else:
            return unsubscribed_listener
       
    def unregister_all(self):
        """
        Returns the list of all listeners that were unsubscribed from the 
        topic tree

        Note: this method will generate one 'unsubcribe' notification message
        for each listener unsubscribed
        """
        unsubscribed_listeners = self._event_bus.unsubAll() 
        return unsubscribed_listeners


class EventLogger(object):
    """ monitors and logs all event traffic over pypubsub """

    def __init__(self):
        self._event_bus = pub 
        self.subscribe_to_all_topics()

    def subscribe_to_all_topics(self):
        self._event_bus.subscribe(self.log_event, self._event_bus.ALL_TOPICS) 

    def log_event(topicObj=pub.AUTO_TOPIC, **kwargs):
        pass  # define later, using structlog if possible