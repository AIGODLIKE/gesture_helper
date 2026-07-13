from bpy.app.translations import pgettext

from ..utils.adapter import operator_invoke_confirm
from ..utils.backups import (
    clear_rotating_gesture_backups,
    format_backup_size,
    get_rotating_backup_stats,
)
from ..utils.public import PublicOperator, poll_addon_preferences


class ClearBackups(PublicOperator):
    bl_idname = 'wm.gesture_clear_backups'
    bl_label = 'Clear Auto Backups'
    bl_description = (
        'Delete all rotating auto-backup files in the active backup folder. '
        'Preferences and gesture data files are not removed. This cannot be undone.'
    )
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, _):
        return poll_addon_preferences(cls)

    def invoke(self, context, event):
        count, total = get_rotating_backup_stats()
        size = format_backup_size(total)
        return operator_invoke_confirm(
            self,
            event,
            context,
            title=pgettext("Clear all auto backups?"),
            message=pgettext(
                "{count} file(s), {size}. "
                "Only rotating auto backups are deleted. This cannot be undone."
            ).format(count=count, size=size),
        )

    def execute(self, _):
        count, total = clear_rotating_gesture_backups()
        if count == 0:
            self.report({'INFO'}, pgettext("No auto backups to clear"))
            return {'FINISHED'}
        size = format_backup_size(total)
        self.report(
            {'INFO'},
            pgettext("Cleared {count} auto backup(s) ({size})").format(
                count=count, size=size,
            ),
        )
        return {'FINISHED'}
