from redis import Redis
import logging


class RedisKV:
    def __init__(self, credentials):
        self.redis = Redis(**credentials)
        self.logger = logging.getLogger(__name__)

    def set_user_event_topic(self, user_id, topic, created_at, ttl=None):
        """
        Add a topic to the user's sorted set with a score (created_at).
        Optionally set a TTL for the key.
        """
        try:
            key = f'user_topics_set:{user_id}'
            self.redis.zadd(key, {topic: created_at})
            if ttl:
                self.redis.expire(key, ttl)
        except Exception as e:
            self.logger.error(f"Failed to set user event topic: {e}")
            raise

    def get_user_topics(self, user_id, top=3):
        """
        Retrieve the top N topics for a user from Redis.
        """
        try:
            key = f'user_topics_set:{user_id}'  # Fixed key formatting
            return [
                topic.decode() for topic in self.redis.zrevrange(key, 0, top - 1)
            ]
        except Exception as e:
            self.logger.error(f"Failed to get user topics: {e}")
            return []
