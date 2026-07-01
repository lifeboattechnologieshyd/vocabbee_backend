from django.db.models import Q
from db.models.user import UserMaster

class RecipientResolver:

    @classmethod
    def resolve(cls, campaign):

        audience_map = {
            "ALL_USERS": cls.all_users,
            "PARENTS": cls.parents,
            "KIDS": cls.kids,
            "GRADES": cls.grades,
            "SPECIFIC_USERS": cls.specific_users,
            "SPECIFIC_KIDS": cls.specific_kids,
            "ACTIVE_USERS": cls.active_users,
            "INACTIVE_USERS": cls.inactive_users,
        }

        resolver = audience_map.get(campaign.audience)

        if not resolver:
            return UserMaster.objects.none()

        return resolver(campaign)


    @staticmethod
    def all_users(campaign):
        return UserMaster.objects.filter(
            is_active=True
        )
    @staticmethod
    def parents(campaign):
        return UserMaster.objects.filter(
            is_active=True,
            role="PARENT"
        )

    @staticmethod
    def kids(campaign):
        return UserMaster.objects.filter(
            is_active=True
        ).distinct()

    @staticmethod
    def grades(campaign):
        return UserMaster.objects.filter(
            kids__grade_id__in=campaign.grade_ids,
            is_active=True
        ).distinct()

    @staticmethod
    def specific_users(campaign):
        return UserMaster.objects.filter(
            id__in=campaign.user_ids,
            is_active=True
        )

    @staticmethod
    def specific_kids(campaign):
        return UserMaster.objects.filter(
            kids__id__in=campaign.kid_ids,
            is_active=True
        ).distinct()

    @staticmethod
    def active_users(campaign):
        return UserMaster.objects.filter(
            is_active=True
        )

    @staticmethod
    def inactive_users(campaign):
        return UserMaster.objects.none()