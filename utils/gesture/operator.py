


class Gestures:
    '''    手势系统分类    '''
    _default_mouse = Vector((0, 0)).freeze()
    draw_handle = None  # 每一个操作符都有退出事件,所以不能共用
    mouse_last_move_time = None  # 鼠标最后移动时间,用于手势超时弹出检测

    gestures_data = {  # 操作符共用属性
        'is_popup_gestures': False,  # 是已经弹出了手势的,只有超时后才会弹出,为True后不会再改变
        'pie_property': None,  # 记录运行操作符之前的饼菜单属性
        'is_normal_exit': True,  # 可正常退出
        'popup_items': [],  # 已弹出项
        'mouse': _default_mouse,

    }

    def _get_active_gestures_item(self) -> 'UIElementItem':
        gi = self.gestures_items
        return gi[-1] if gi else None

    def _set_active_gestures_item(self, value):
        self.gestures_items.append(value)

    def _set_is_popup_gestures(self, value):
        self.gestures_data['is_popup_gestures'] = value

    def _set_pie_property(self, value):
        self.gestures_data['pie_property'] = value

    def _set_is_normal_exit(self, value):
        self.gestures_data['is_normal_exit'] = value

    def _set_mouse(self, value):
        self.gestures_data['mouse'] = value

    active_gestures_item = property(_get_active_gestures_item,
                                    _set_active_gestures_item,
                                    doc='活动手势项,默认无,只有进入了子手势项才会设置',
                                    )
    is_popup_gestures = property(lambda self: self.gestures_data['is_popup_gestures'],
                                 _set_is_popup_gestures
                                 )

    pie_property = property(lambda self: self.gestures_data['pie_property'],
                            _set_pie_property
                            )
    is_normal_exit = property(lambda self: self.gestures_data['is_normal_exit'],
                              _set_is_normal_exit
                              )
    mouse = property(lambda self: self.gestures_data['mouse'],
                     _set_mouse
                     )
    gestures_items = []
    mouse_point = []
    mouse_path = []
    mouse_path_3d = []

    # DrawGui

    def draw_gestures(self,):
        """
        绘制手势
        多区域绘制问题 不移动鼠标即可
        """
        gpu.state.blend_set('ALPHA')
        # bgl.glEnable(bgl.GL_BLEND)nn
        # bgl.glEnable(bgl.GL_ALPHA)
        # bgl.glDisable(bgl.GL_DEPTH_TEST)

        if not self.is_popup_gestures:
            bbpy.gpu.draw_2d_line(self.mouse_path, (1.0, 1.0, 1.0, 1), 1)
        else:
            bbpy.gpu.draw_2d_line(
                self.mouse_point+[self.mouse, ], (1.0, 0.5, 0.5, 1), 3.4)
            bgl.glPointSize(10)
            shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
            batch = batch_for_shader(
                shader, 'POINTS', {"pos": self.mouse_point})
            shader.bind()
            shader.uniform_float("color", (1, 1, 1, 0.5))
            batch.draw(shader)
            bgl.glPointSize(1)

        text = str(self.gestures_direction)+' '*4+str(self.gestures_distance)
        bbpy.gpu.draw_text(text=text,
                           size=50, color=(1, 0, 0, 1))
        text = str(
            [i.uuid if i else i for i in self.gestures_direction_items])
        bbpy.gpu.draw_text(text, 20, 100, 400)
        text = str(self.gestures_point_item)
        bbpy.gpu.draw_text(text, 20, 100, 300)
        text = str(self.active_gestures_item)
        bbpy.gpu.draw_text(text, 20, 100, 200)

        text = 'mouse_point' + str(self.mouse_point)
        bbpy.gpu.draw_text(text, 20, 100, 450)

        text = 'gestures_items' + str(self.gestures_items)
        bbpy.gpu.draw_text(text, 20, 100, 500)

        gpu.state.blend_set('NONE')

    def add_handler(self):
        if not self.draw_handle:
            self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_gestures, (), 'WINDOW', 'POST_PIXEL')

    def del_handler(self):
        if self.draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(
                self.draw_handle, 'WINDOW')

    # 子级 menu_pie 弹出菜单
    child_gestures_uuid: StringProperty(**SKIP_DEFAULT,)
    popup_menu_pie_mouse_x: IntProperty(default=0, **SKIP_DEFAULT,)
    popup_menu_pie_mouse_y: IntProperty(default=0, **SKIP_DEFAULT,)
    is_gestures_popup: BoolProperty(name='是手势弹出的')

    gestures_direction_items = property(lambda self: self.item.__get_gestures_direction_items__(self.active_gestures_item),
                                        doc='当前项'
                                        )
    # gestures property

    is_use_gestures = property(lambda self: bool(self.item) & self.item.use_gestures & self.is_menu_pie,
                               doc='是使用手势的')

    def __gestures_dire__(self, angle: float,  split=22.5) -> int:
        """获取手势朝向的整数值

        Args:
            angle (float): _description_
            split (float, optional): _description_. Defaults to 22.5.

        Returns:
            int: _description_
        """
        an = abs(angle)
        if split < an < (split+45):
            return 5 if angle < 0 else 7
        elif (90-split) < an < (90+split):
            return 4 if angle < 0 else 3
        elif (90+split) < an < (90+split+45):
            return 6 if angle < 0 else 8

    @property
    def gestures_direction(self, split=22.5) -> int:
        """获取手势的朝向 index(8个方向)

        Args:
            split (float, optional): _description_. Defaults to 22.5.

        Returns:
            int: _description_
        """
        vector = self.mouse - self.mouse_point[-1]
        if vector == Vector((0, 0)):
            return -1  # 没有任何朝向
        angle = (180 * vector.angle_signed(Vector((-1, 0)))) / pi

        max_split = 180 - split

        if -split < angle < split:
            return 1
        elif (max_split < angle) | (angle < -max_split):
            return 2
        else:
            return self.__gestures_dire__(angle)

    def __gestures_distance__(self, mouse_co=None) -> float:
        """获取手势移动的距离

        Args:
            mouse_co (_type_, optional): _description_. Defaults to None.

        Returns:
            float: _description_
        """
        return (self.mouse - (mouse_co if mouse_co else self.mouse_point[-1])).magnitude
    gestures_distance = property(__gestures_distance__)

    @property
    def gestures_beyond_distance(self) -> bool:
        '''获取手势超出规定距离的布尔值
        如果没弹出 距离按半径
        弹出了就按阈值
        '''
        def get_pro(pro):
            act_prop = getattr(self.item, pro, 60)  # 当前项的值
            pref_prop = getattr(self.prefs, pro, 60)  # 预设的值
            attr = act_prop if act_prop else pref_prop
            return attr
        is_p = self.is_popup_gestures
        typ = 'pie_menu_confirm' if is_p else 'pie_menu_radius'
        attr = get_pro(typ)
        attr += attr * (0.3 if is_p else 0.15)
        return self.gestures_distance > attr

    @property
    def gestures_point_item(self) -> 'UIElementItem':
        """获取手势指向项

        Returns:
            UIElementItem: _description_
        """
        act = self.active_gestures_item
        dire = self.gestures_direction
        items = self.item.__get_gestures_direction_items__(act)

        if not dire:
            return

        switch_dire = {3: 4, 4: 3}
        dire = switch_dire[dire] if dire in switch_dire else dire

        index = dire-1  # ERROR上下颠倒
        return items[index] if dire else None

    @property
    def gestures_is_allow_child(self) -> bool:
        """获取手势是可作为子级的布尔值

        Returns:
            bool: _description_
        """
        pot = self.gestures_point_item
        allow_type = pot and pot.is_allow_child_type
        is_child = pot and (pot.child_as_gestures_item and allow_type)
        return bool(is_child)

    @property
    def is_beyond_distance_event(self) -> bool:
        """获取 手势超出距离 并且朝向的项是有效的布尔值

        Returns:
            _type_: _description_
        """
        return self.gestures_beyond_distance and self.gestures_point_item

    @property
    def is_beyond_child(self) -> bool:
        """获取超出并且是子级的布尔值

        Returns:
            _type_: _description_
        """
        return self.gestures_is_allow_child and self.is_beyond_distance_event
    gestures_is_operator = property(lambda self:
                                    self.gestures_point_item and
                                    (self.gestures_point_item.type == 'operator'),
                                    doc='手势是操作符'
                                    )

    @classmethod
    def restore_gestures_data(cls) -> None:
        '''恢复数据
        在退出时重置为默认数据
        '''
        cls.is_popup_gestures = False
        cls.pie_property = None
        cls.is_normal_exit = True
        cls.mouse = cls._default_mouse

        cls.gestures_items.clear()
        cls.mouse_point.clear()
        cls.mouse_path.clear()
        cls.mouse_path_3d.clear()
        print('restore_gestures_data')

    def key_test(self) -> None:
        """模拟enter键测试
        """
        import keyboard

        keyboard.press('enter')

    def exit_pie(self) -> None:
        '''
        退出当前饼菜单
        使用模拟esc键来退出
        右键的话可能和用户设置的快捷键冲突
        '''
        import keyboard
        keyboard.release('esc')
        print('模拟esc点击退出饼菜单', self.gestures_items, '\n', self.mouse_point)

    def set_gestures_data(self) -> None:
        """设置手势数据
        """
        point_item = self.gestures_point_item
        self.active_gestures_item = point_item
        self.child_gestures_uuid = point_item.uuid  # 设置子级
        self.mouse_point += [self.mouse, ]  # 添加点

    def gestures_return_previous_item(self) -> bool:  # 反回之前项
        """是否反回之前的项
        绘制point点,如果鼠标放在上面则回退到鼠标指的那个点
        如果放在一个项上超时,则执行此项

        Returns:
            bool: _description_
        """

        if self.is_popup_gestures:
            for index, mouse in enumerate(self.mouse_point[:-1]):
                distance = self.__gestures_distance__(mouse_co=mouse)
                if distance < 10:
                    print('\t\tdistance < 10')
                    print(self.mouse_point)
                    print(self.gestures_items)
                    self.exit_pie()
                    self.mouse_point[index+1:] = []
                    self.gestures_items[index:] = []
                    self.is_normal_exit = False
                    return True
        return False

    def overtime(self) -> set:  # 超时
        """超时弹出手势

        Returns:
            set: _description_
        """
        print('\t超时弹出手势\tself.is_overtime and (not self.is_popup_gestures)')
        self.mouse_point[-1] = self.mouse  # -1
        self.is_popup_gestures = True
        self.rerunning_operator()
        return {'RUNNING_MODAL'}

    def not_is_normal_exit(self) -> set:
        """不是正常退出

        Returns:
            _type_: _description_
        """
        event = self.event

        if self.is_normal_exit == None:
            self.is_normal_exit = True
        elif self.none_event:
            # 饼菜单退出事件
            self.mouse_point[-1] = self.mouse
            self.rerunning_operator()
            self.is_normal_exit = None
        elif event.type not in ('NOTHING', 'TIMER', 'TIMER_REPORT', 'NONE'):
            print(
                f"说明退出来了 event.type  {event.type} not in ('NOTHING', 'TIMER', 'TIMER_REPORT')")
            self.mouse_point[-1] = self.mouse
            self.rerunning_operator()
            self.is_normal_exit = None
        else:
            print('是需要退出饼菜单的,但移鼠标太快了,退出键被覆盖了,再退出一次吧')
        print(
            f'is_normal_exit:{self.is_normal_exit}\none_event:{self.none_event}\tgestures_items{[i.uuid for i in self.gestures_items]}\ttype:{event.type}\tvalue:{event.value}')
        self.key_test()
        return {'RUNNING_MODAL'}

    def operator_point_item(self) -> set:
        """是 释放键

        Returns:
            set: _description_
        """
        print("operator_point_item")
        point_item = self.gestures_point_item
        if self.gestures_is_operator and (not self.is_popup_gestures):
            print(
                '运行操作符,self.gestures_is_operator and (not self.is_gestures_popup) ', point_item)
            point_item.running_operator()
            self.exit_pie()
            self.is_normal_exit = None
        return {'PASS_THROUGH', 'FINISHED'}

    def gestures_popup_manage_handle(self) -> set:  # 弹出了处理
        """弹出了处理

        Returns:
            set: _description_
        """
        ex = self.is_normal_exit
        is_return_item = self.gestures_return_previous_item()

        if not ex:
            return self.not_is_normal_exit()
        elif self.release:
            return {'FINISHED'}
        elif is_return_item:
            return {'RUNNING_MODAL'}
        elif self.is_beyond_child:
            print(
                f'手势子级可用\tself.gestures_is_allow_child\tpoint_item:{self.gestures_point_item}')
            self.is_normal_exit = False
            self.set_gestures_data()
            self.exit_pie()
        elif self.none_event:
            print('self.none_event')
            self.operator_point_item()
            self.is_normal_exit = None
            self.exit_pie()
            return {'FINISHED'}
        elif self.is_exit:
            print('self.is_exit')
            return {'FINISHED'}
        else:
            print('gestures_popup_manage\t\tpass')
        return {'RUNNING_MODAL'}

    def gestures_not_popup_manage_handle(self) -> set:  # 没弹出处理
        """没弹出处理

        Returns:
            set: _description_
        """
        no_popup_gestures = (not self.is_popup_gestures)
        point_item = self.gestures_point_item
        if self.is_overtime and no_popup_gestures and self.is_normal_exit:
            # 是超时了并且没有弹出窗口的,第一个弹出必是从这里
            return self.overtime()
        elif self.release:

            if self.gestures_is_operator:
                point_item.running_operator()
                self.is_popup_gestures = True
            return {'FINISHED'}
        elif self.is_beyond_distance_event:
            if self.gestures_is_allow_child:
                # 还在移动鼠标手势当中,不弹出
                self.set_gestures_data()
        else:
            print('gestures_not_popup_manage\tpass')
        return {'RUNNING_MODAL'}

    # @bbpy.debug.time
    def gestures_modal(self) -> set:
        '''
        手势模态
        通过鼠标的行为设置弹出窗口 ✅
        识别按手势的来弹出 ✅
            退出手势:
            手势弹出子级时退出之前显示项
        不弹出手势菜单时运行项 ✅
        将鼠标位置放在类里面 ✅
        # 如果弹出菜单了通过饼菜单自身的阈值来确认操作符(进入子级)
        # 如果没有弹出则自已来判断应该设置那个子级
        '''
        event = self.event
        print(Fore.RED+'\tgestures_modal', event.type, event.value,
              '\n\tis_popup_gestures', self.is_popup_gestures,
              '\tis_exit', self.is_exit,
              '\trelease', self.release,
              '\tis_normal_exit', self.is_normal_exit,
              Fore.RESET)

        if self.is_popup_gestures:
            return self.gestures_popup_manage_handle()
        else:
            return self.gestures_not_popup_manage_handle()

    # @bbpy.debug.time
    def popup_gestures(self, context: 'bpy.context', event: 'bpy.types.Event') -> None:
        """
        边界保护,如果超过规定的距离就弄回来 暂时不用做这个

        校正鼠标位置,但如果在其它视图将会出现问题,所以ban了
        mo = self.mouse
        # if mo and area:
        #     context.window.cursor_warp(x=int(mo[0])+area.x,
        #                                y=int(mo[1])+area.y
        #                                )
        """
        self.child_gestures_uuid

        data = {
            'title': self.child.ui_element_name if self.child else self.item.ui_name}
        x = self.popup_menu_pie_mouse_x
        y = self.popup_menu_pie_mouse_y
        area = context.area

        if (x != 0) and (y != 0) and area:
            # 设置鼠标位置到输入的位置
            context.window.cursor_warp(x=x+area.x, y=y+area.y)

        print(f'弹出手势 popup_gestures popup_menu_pie\tx:{x}\ty:{y}\tdata:{data}')
        self.wm.popup_menu_pie(event, self.draw_generate_func, **data)


class Popup:
    wm = property(lambda _: bpy.context.window_manager)

    def popup_menu(self, context: 'bpy.context', event: 'bpy.types.Event') -> None:
        data = {}
        self.wm.popup_menu(self.draw_generate_func, **data)

    def popup_draw_func(self, context: 'bpy.context', event: 'bpy.types.Event') -> set:
        """
        invoke_props_dialog
        invoke_confirm
        invoke_search_popup
        invoke_props_popup
        invoke_popup
        popover
        """
        if self.is_menu_pie:
            self.popup_gestures(context, event)
        else:
            self.popup_menu(context, event)
        return {'FINISHED'}


class Modal:
    def modal_double_key(self, context: 'bpy.context', event: 'bpy.types.Event') -> set:
        """
        双键模态
        如
        exit_type = value not in (
            'TIMER', 'INBETWEEN_MOUSEMOVE', 'MOUSEMOVE')
            | exit_type
        """

        print(event.type, event.value, self.key.double_key)
        if event.type in self.double_key['keys']:
            self.rerunning_operator(uuid=self.double_key[event.type])
            return {'FINISHED'}
        elif self.is_overtime:
            return {'PASS_THROUGH', 'FINISHED'}
        else:
            return {'PASS_THROUGH'}

    def modal_long_press(self, context: 'bpy.context', event: 'bpy.types.Event') -> set:
        '''
        长按模态
        如果按了其它键或是移动了鼠标则退出,只有按下后一直按不执行其它按键时才可以
        bbpy.debug.print_dir(event)
        typ = (event.type not in ('TIMER', 'MOUSEMOVE'))
        '''

        if event.value != 'NOTHING':
            print("\tevent.value != 'NOTHING'")
            return {'PASS_THROUGH', 'FINISHED'}
        if self.is_overtime:
            self.rerunning_operator()
            return {'FINISHED'}
        else:
            return {'PASS_THROUGH'}

    def operator_modal(self, context: 'bpy.context', event: 'bpy.types.Event'):
        '''运行对应操作符模态
        '''
        ret = {'PASS_THROUGH', 'FINISHED'}

        if self.is_use_double:
            ret = self.modal_double_key(context, event)
        elif self.is_use_long_press:
            ret = self.modal_long_press(context, event)
        elif self.is_use_gestures:
            ret = self.gestures_modal()
        return ret


class Handle:

    def prepare_pie_prop(self) -> None:  # 饼菜单
        """设置饼菜单属性
        """

        if self.store_pie_prop and (not self.pie_property):
            # 如果是饼菜单则记录原始饼菜单属性,并设置为绘制项设置的饼菜单属性
            view = self.context.preferences.view
            prop = pie_property_items
            self.pie_property = {i: getattr(view, i, 0) for i in prop}
            for pro in prop:
                act_prop = getattr(self.item, pro, 0)  # 当前项的值
                pref_prop = getattr(self.prefs, pro, 20)  # 预设的值
                attr = act_prop if act_prop else pref_prop
                setattr(view, pro, attr)

            # if self.is_use_gestures:
            #     # 如果是手势则禁用确认阈值,使用手动弹出窗,而不是让饼菜单自已超出阈值后弹出
            #     view.pie_menu_confirm = 0

    def prepare_double_prop(self) -> None:  # 双键
        """双键时 设置属性
        """
        if self.is_use_double:
            self.double_key = text_info = self.double_keys[self.key.key_combination]
            text = f'双键\t\t\t可按下: {str(text_info["keys"])[1:-1]}  等待时间(ms):{self.await_time}'
            area = self.context.area
            if area:
                area.header_text_set(text)

    def prepare_handle(self, context: 'bpy.context', event: 'bpy.types.Event', mode: str) -> None:  # 预处理数据
        """预处理一些数据

        Args:
            context (bpy.context): _description_
            event (bpy.types.Event): _description_
            mode (str): _description_
        """
        event_none = (event.type == 'NONE')
        event_nothing = (event.value == 'NOTHING')
        self.event = event
        self.context = context

        # gestures property
        self.exit_key = (event.type in {'RIGHTMOUSE', 'ESC'})  # 退出键
        self.release = (event.value == 'RELEASE')  # 释放键
        # pie的退出事件,在退出pie时会是这个数据
        self.none_event = (event_none and event_nothing)
        self.pie_exit = (self.none_event)  # 是模拟键退出饼菜单
        self.key_exit = (
            self.exit_key and self.release)
        self.is_exit = (self.pie_exit or self.key_exit) and self.is_normal_exit

        self.store_pie_prop = self.is_menu_pie and (not self.pie_property)
        self.prepare_pie_prop()
        self.prepare_double_prop()

    def exit_handle(self, context: 'bpy.context', event: 'bpy.types.Event', return_set: set, mode: str) -> None:
        '''
        退出时处理数据
        RUNNING_MODAL
        CANCELLED
        FINISHED
        PASS_THROUGH
        INTERFACE
        '''
        is_modal = (mode == 'modal')  # else is invoke
        is_exit = True in ((i in return_set)
                           for i in ('CANCELLED', 'FINISHED'))

        if is_exit:
            self.del_handler()  # 删除绘制handler

            restore_pie_property = (is_modal | (
                not self.is_use_modal)) and self.pie_property
            area = context.area

            if area:
                area.header_text_set(None)  # 重置顶栏文本

            if restore_pie_property:
                view = context.preferences.view
                for pro in self.pie_property:
                    setattr(view, pro, self.pie_property[pro])

            print('\tis_exit  self.del_handler() ', event.type,
                  event.value, return_set, mode)

            if is_modal:
                print('self.gestures_data:')
                for i in self.gestures_data:
                    print('\t', i, self.gestures_data[i])
                print(f'\tgestures_items:{self.gestures_items}')
                print(f'\tmouse_point:{self.mouse_point}')
                print(f'\tmouse_path:{self.mouse_path}')
                self.restore_gestures_data()
                print('_'*60, '\n\n\n')
        print(context.area.type, context.region.type)
        context.region.tag_redraw()

        # self.tag_redraw()

    def modal_handle(func):
        '''
        处理进入或退出模态或方法
        添加更改或删除数据
        '''
        @wraps(func)
        def decorated(*args, **kwargs):
            mode = 'invoke' if func.__name__ == 'invoke_handle' else 'modal'
            self = args[0]
            self.prepare_handle(*args[1:], mode)
            ret = func(*args, **kwargs)
            self.exit_handle(*args[1:], ret, mode)

            if not self.is_popup_gestures:
                '''
                ERROR 键位冲突 如果还没弹出手势则通过
                如果设置的右键,可以实现马上松鼠标的话还是显示右键菜单(将右键弹出菜单设置成松开)
                '''
                ret.add('PASS_THROUGH')

            return ret
        return decorated

    @modal_handle
    def invoke_handle(self, context, event) -> set:
        """
        使用模态来设置 长按和双键的设置
        """

        not_direct = (not self.direct_draw)
        is_modal = self.is_use_modal and not_direct

        text = self.bl_idname+'\tinvoke' + \
            f'\n\tis_use_modal:{self.is_use_modal}\tis_modal:{is_modal}' +\
            f'\n\tnot_direct:{not_direct}' +\
            f'\n\tis_menu_pie:{self.is_menu_pie}'

        print(Fore.GREEN+text+Fore.RESET)
        if is_modal:
            '''
            需要进入模态
            长按 双键 或是手势的时候才需要进入模态
            如果需要直接绘制则不进入模态,直接进行绘制
            '''
            # 自定义触发方式,只有是
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL', 'PASS_THROUGH'}
        return self.popup_draw_func(context, event)

    @modal_handle
    def modal_handle(self, context, event) -> set:

        self.mouse = mouse = Vector((event.mouse_region_x,
                                     event.mouse_region_y)).freeze()

        if (mouse != self.mouse_path[-1]) and self.is_use_gestures and (not self.is_popup_gestures):
            self.mouse_last_move_time = time()  # 鼠标最后移动的时间
            self.mouse_path.append(mouse)  # 鼠标路径

        if self.is_use_modal:
            # 如果使用模态并且
            return self.operator_modal(context, event)
        else:
            print("return {'FINISHED'} ", event.type)
            return {'FINISHED'}


class Property:
    # property()
    item = property(lambda self: self.prefs.ui_items.get(
        self.uuid), doc='通过self.uuid获取需要绘制的项')
    child = property(lambda self: self.item.ui.get(
        self.child_gestures_uuid), doc='反回child_gestures_uuid项')

    key = property(lambda self: self.item.key, doc='获取需要绘制的项的key')

    @property
    def await_time(self) -> float:
        """
        获取长按或双键需要等待的时间
        如果当前项设置为0那么则使用默认属性
        """
        key = self.key
        prefs = self.prefs

        if self.is_use_double:
            k_tim = key.double_key_time
            tim = k_tim if k_tim else prefs.double_key_time
        elif self.is_use_long_press:
            l_tim = key.long_press_time
            tim = l_tim if l_tim else prefs.long_press_time
        elif self.is_use_gestures:
            tim = prefs.gestures_await_time
        return tim * .001  # 换算成s

    @property
    def is_overtime(self) -> bool:
        """是超时的(操作符运行时间超过设定值)
        通过获取模态运行的时间和设定的超时时间
        来判断当前运行模态的时间是否超时
        如果超过设定的时间则判定为超时

        在双键 长按 手势 这些模式使用
        """
        if self.is_use_gestures:
            # 鼠标最后移动时间
            self.running_time = time() - self.mouse_last_move_time
        else:
            # 模态总运行时间
            self.running_time = time() - self.start_time

        return self.running_time > self.await_time  # 超时 模态运行时间超过最大值

    is_use_double = property(lambda self:
                             self.key.value == 'DOUBLE_KEY',
                             doc='是双键触发的')
    is_use_long_press = property(lambda self:
                                 self.key.value == 'LONG_PRESS',
                                 doc='是长按触发的')
    is_use_modal = property(lambda self: self.is_use_gestures |
                            self.is_use_long_press | self.is_use_double,
                            doc='是需要进入模态的，使用模态的'
                            )
    is_menu_pie = property(
        lambda self: self.item and (self.item.type == 'menu_pie'), doc='是否为饼菜单')


class ExecuteOperator(bbpy.types.Operator,
                      Data,
                      Gestures,
                      Property,
                      Handle,
                      Popup,
                      Modal,
                      ):
    bl_idname = 'ui.custom_ui_operator'
    bl_label = f'''{bbpy.get.addon.name()}Custom UI 操作符项'''
    # bl_options = {'INTERNAL', 'UNDO', 'UNDO_GROUPED'}  #
    # 'REGISTER',, 'UNDO_GROUPED'

    uuid: StringProperty(**SKIP_DEFAULT,)

    value: EnumProperty(name='触发方式', **kmi_value,
                        default='PRESS')

    direct_draw: BoolProperty(name='直接绘制',
                              description='直接绘制,不进行其它判断',
                              default=False,
                              **SKIP_DEFAULT)

    def rerunning_operator(self, uuid=None) -> None:
        '''
        重新运行一遍自身操作符,但是是直接绘制
        '''

        data = {
            'uuid': uuid if uuid else self.uuid,
            'direct_draw': True,
        }
        is_gestures = self.is_use_gestures
        act = self.active_gestures_item
        data['is_gestures_popup'] = is_gestures
        if is_gestures:
            mo = self.mouse_point[-1] = self.mouse  # 将最后点改成当前鼠标点弹出进行时
            if self.is_gestures_popup:
                x = mo[0]
                y = mo[1]
                data.update({'popup_menu_pie_mouse_x': int(x),
                            'popup_menu_pie_mouse_y': int(y),
                             })
        if act:
            data['child_gestures_uuid'] = act.uuid

        bpy.ops.ui.custom_ui_operator('INVOKE_DEFAULT',
                                      **data,
                                      )

        text = f'bpy.ops.ui.custom_ui_operator (\t{data})\tactive_gestures_item:{act} is_gestures_popup:{self.is_gestures_popup}'
        print(text)

    @bbpy.debug.time
    def draw_generate_func(self, draw, context) -> None:
        draw_data = {}
        item = self.item.ui.get(self.child_gestures_uuid)
        print('\t\t\tdraw_generate_func', item, self.child_gestures_uuid)

        if self.is_use_gestures:
            self.item.draw_gestures(
                draw.layout,
                item
            )
        else:
            self.item._draw_func(draw.layout, direct_draw=True, **draw_data)

    # handle

    def invoke(self, context, event) -> set:
        print('invoke')

        self.mouse_last_move_time = self.start_time = time()  # 记录开始时间

        self.mouse = Vector((event.mouse_region_x,
                            event.mouse_region_y)).freeze()  # 记录开始鼠标

        self.mouse_window = Vector((event.mouse_x,
                                    event.mouse_y)).freeze()

        self.mouse_path = [self.mouse, ]
        self.mouse_point = self.mouse_path.copy()

        if not self.draw_handle:
            self.add_handler()

        return self.invoke_handle(context, event)

    def modal(self, context, event) -> set:
        return self.modal_handle(context, event)


class PopupMenu(bbpy.types.Operator):
    bl_idname = 'ui.custom_ui_popup_menu'
    bl_label = f'''{addon_name} 弹出UI设置菜单'''

    # 用于设置弹出菜单的活动项
    uuid: StringProperty(**SKIP_DEFAULT,)
    ui_uuid: StringProperty(**SKIP_DEFAULT,)
    popup_type: StringProperty(default='popup_menu', **SKIP_DEFAULT,)

    def draw(self, context) -> None:
        self.draw_func(context)

    def draw_func(self, context) -> None:
        DrawCustomUiFunc.draw(self, self.layout, context)

    def draw_menu(self, enum, context) -> None:
        DrawCustomUiFunc.draw(self, enum.layout, context)

    def invoke(self, context, event) -> set:
        self.prefs = Data.prefs.fget()
        self.tmp_kmi = Data.tmp_kmi.fget()
        self.act_ui_item = Data.act_ui_element.fget()
        self.act_ui_element = Data.act_ui_item.fget()

        typ = self.popup_type
        wm = context.window_manager
        if typ == 'invoke_props_dialog':
            return wm.invoke_props_dialog(operator=self, width=800)
        elif typ == 'popup_menu':
            wm.popup_menu(self.draw_menu, title=f'{addon_name}  UI属性')
        elif typ == 'window':
            # TODO  context is incorrect
            bpy.ops.wm.window_new('INVOKE_DEFAULT')
            wm.windows[-1].screen.areas[-1].type = 'PREFERENCES'
            context.preferences.active_section = 'ADDONS'
        return {'FINISHED'}

    def execute(self, context) -> set:
        """
        占位
        如果不添加将会弹出错误
        """
        text = f'{self.bl_idname}, execute {self}'
        print(text)
        return {'FINISHED'}


class DrawCustomUiFunc(Data):
    class UIElementMenu(bpy.types.Menu, Data):
        bl_idname = 'UI_MT_CUSTOM_UI_ELEMENT'
        bl_label = 'ui元素菜单'

        def draw(self, context):
            pref = bbpy.get.addon.prefs().custom_ui

            layout = self.layout
            layout.prop(pref, 'show_advanced_options')
            layout.prop(pref, 'modifier_preset_data')

    def draw_generate_ui(self, layout: bpy.types.UILayout):
        layout.use_property_split = False
        layout.use_property_decorate = True

        item = self.act_ui_item

        if self.is_debug:
            DrawCustomUiFunc.draw_test(self, layout)

        if item:
            column = layout.column(align=True)
            column.label(text='preview:')
            item._draw_func(column, preview=True)

            column = layout.column(align=True)
            column.label(text='edit:')
            item._draw_func(column, preview=False)
            ...

    # draw
    def draw(self, layout: bpy.types.UILayout, context: bpy.context):
        """
        绘制自定义ui面板
        preferences调用
        """
        layout.operator_context = 'INVOKE_DEFAULT'
        Data.injection_attribute(self)
        self.is_debug = bbpy.get.addon.prefs().debug.custom_ui

        self.item_len = len(self.prefs.ui_items)
        enable_ui = self.act_ui_item and self.prefs.edit_ui_item
        self.edit_mode = (enable_ui and len(self.act_ui_item.ui))

        if self.is_debug:
            is_draw, lay = draw_extend_ui(
                layout, 'draw_keymaps_ui_head', label='ui property')

            if is_draw:
                lay.label(text='ui_items'+str(len(self.prefs.ui_items)))
                lay.separator(factor=5)
                for pro in self.prefs.bl_rna.properties:
                    if pro.identifier not in ('name', 'rna_type'):
                        lay.prop(self.prefs, pro.identifier)

        column = layout.column(align=True)
        row = column.row(align=True)
        DrawCustomUiFunc.draw_head(self, row, context)

        column.separator()
        if self.prefs.edit_default_property:
            DrawCustomUiFunc.draw_default_property(self, column, context)
        else:
            sp = column.split(align=True)
            DrawCustomUiFunc.draw_left_area(self, sp, context)
            DrawCustomUiFunc.draw_right_area(self, sp, context)

    def draw_head(self, layout: bpy.types.UILayout, context: bpy.context):
        r"""
        row.prop(prefs, 'show_advanced_options')
        row.prop(prefs, 'modifier_preset_data')
        """
        split = layout.split(align=False, factor=0.5)

        row = split.row()
        prefs = self.prefs
        icon = 'CHECKBOX_HLT' if self.prefs.is_enabled else 'CHECKBOX_DEHLT'
        row.prop(self.prefs, 'is_enabled', text='', icon=icon)

        icon = 'FULLSCREEN_EXIT' if self.prefs.is_full_windows else 'FULLSCREEN_ENTER'
        row.prop(self.prefs, 'is_full_windows', text='', icon=icon)
        row.prop(self.prefs, 'edit_default_property', icon_value=get_icon('e'))

        idname = ExecuteOperator.bl_idname
        ui = self.act_ui_item
        row = split.row(align=True)
        op = row.operator(idname, icon='RESTRICT_VIEW_OFF', text='')
        if ui:
            op.uuid = ui.uuid
            op.direct_draw = True

        ro = row.row()
        ro.alert = prefs.is_red_show_active_item
        ro.prop(prefs, 'is_red_show_active_item', icon='PROP_CON',
                text='',
                )

        # row.prop(prefs, 'edit_ui_item')
        row.prop(prefs, 'only_show_active_need_drawn')

    def draw_default_property(self, layout: bpy.types.UILayout, context: bpy.context):
        prefs = self.prefs
        layout.prop(prefs, 'default_add_poll_is_expression')
        layout.prop(prefs, 'text_sync_update')
        layout.separator()
        layout.prop(prefs, 'double_key_time')
        layout.prop(prefs, 'long_press_time')
        layout.prop(prefs, 'gestures_await_time')
        layout.separator()
        layout.prop(prefs, 'pie_animation_timeout')
        layout.prop(prefs, 'pie_initial_timeout')
        layout.prop(prefs, 'pie_menu_confirm')
        layout.prop(prefs, 'pie_menu_radius')
        layout.prop(prefs, 'pie_menu_threshold')
        layout.prop(prefs, 'pie_tap_timeout')

    def draw_left_area(self, layout: bpy.types.UILayout, context: bpy.context):
        column = layout.column()
        if self.edit_mode:
            DrawCustomUiFunc.draw_generate_ui(self, column)
        else:
            rows = 3
            if self.item_len:
                rows = 7
            row = column.row(align=True)
            col = row.column(align=True)
            col.operator(UIItem.Add.bl_idname, text='', icon='ADD')
            col.operator(UIItem.Del.bl_idname, text='', icon='REMOVE')
            col.operator(UIItem.Duplicate.bl_idname, text='', icon='COPYDOWN')
            col.separator()
            col.operator(UIItem.Move.bl_idname,
                         text='',
                         icon='SORT_DESC').next = False
            col.operator(UIItem.Move.bl_idname,
                         text='',
                         icon='SORT_ASC').next = True

            row.template_list(uilist.UI_UL_Custom_ui.__name__, '',
                              self.prefs, 'ui_items',
                              self.prefs, 'active_index',
                              rows=rows,
                              )

    def draw_right_area(self, layout: bpy.types.UILayout, context: bpy.context):
        column = layout.column()
        if self.item_len:  # 绘制活动项
            DrawCustomUiFunc.draw_item_other_property(self, column)  # 上
            DrawCustomUiFunc.draw_ui_element_items_list(self, column)  # 中
            DrawCustomUiFunc.draw_element_active(self, column)  # 下
            if not self.edit_mode:
                DrawCustomUiFunc.draw_generate_ui(self, column)  # 绘制预览
        else:
            column.label(text='请先添加一个项目或选中项目')

    # draw element
    def draw_ui_element_items_list(self, layout: bpy.types.UILayout):
        r"""
        生成绘制方法
        col.prop(self.prefs, 'edit_ui_item', icon='HIDE_OFF', text='')
        col.prop(self.prefs, 'edit_ui_item', icon='PREFERENCES', text='')
        TODO  UI_UL_CustomUILayout拖慢整个invoke
        """
        item = self.act_ui_item

        column = layout.column()
        ui_len = len(item.ui)

        rows = 3
        if ui_len:
            rows = 7

        row = column.row(align=True)
        # listen
        row.template_list(uilist.UI_UL_CustomUILayout.__name__, '',
                          item, 'ui',
                          item, 'active_ui_index',
                          rows=rows,
                          )

        # right
        col = row.column(align=True)
        DrawCustomUiFunc._right_column(self, col)

    def _right_column(self, col):
        def ops(layout: bpy.types.UILayout, icon):
            layout.operator_context = 'INVOKE_DEFAULT'

            return layout.operator(ElementChange.ElementMove.bl_idname,
                                   text='',
                                   icon=icon,
                                   )

        item = self.act_ui_item
        ui = self.act_ui_element
        op = col.operator(ElementChange.ElementAdd.bl_idname,
                          text='', icon='ADD')
        op.uuid = item.uuid
        if ui:
            op.ui_element_uuid

        op = col.operator(ElementChange.ElementDel.bl_idname,
                          text='', icon='REMOVE')
        op.uuid = item.uuid
        if ui:
            op.ui_element_uuid

        col.operator(ElementChange.ElementDuplicate.bl_idname,
                     text='',
                     icon='COPYDOWN',
                     )

        op = col.operator(ElementChange.ElementAdd.bl_idname,
                          text='', icon='RNA_ADD')
        op.uuid = item.uuid
        op.is_add_select_structure_type = True
        if ui:
            op.ui_element_uuid

        col.separator()
        if item.is_moving():
            op = ops(col, 'ALIGN_LEFT')
            op.move_to_uuid = ''

            op = ops(col, 'CANCEL')
            op.exit_move = True
        else:
            op = ops(col, 'TRIA_UP')
            op.type = 'UP'
            op = ops(col, 'GRIP')
            if ui:
                op.move_item_uuid = ui.uuid

            op = ops(col, 'TRIA_DOWN')
            op.type = 'DOWN'
        col.separator()

        # col.separator(factor=3)
        col.menu(DrawCustomUiFunc.UIElementMenu.bl_idname,
                 text='',
                 icon='SETTINGS'
                 )
        icon = 'ANCHOR_LEFT' if self.prefs.edit_ui_item else 'ANCHOR_RIGHT'
        col.prop(self.prefs, 'edit_ui_item', text='', icon=icon)
    # active property

    def draw_element_active(self, layout: bpy.types.UILayout):
        """
        绘制活动项element的参数,启用高级输入
        """
        ui = self.act_ui_element
        if ui:
            column = layout.column()
            DrawCustomUiFunc.draw_element_item_props(self, column)
            DrawCustomUiFunc.draw_element_advanced_parameter(self, column)
        else:
            layout.label(text='请选择一个活动项或新建一个')

    def draw_element_item_props(self, layout: bpy.types.UILayout):
        """
        绘制活动项的一些需要设置的属性
        """
        item = self.act_ui_item
        ui = self.act_ui_element
        typ = ui.type

        if item.is_use_gestures:
            row = layout.row()
            row.prop(ui, 'gestures_direction')
            if ui.is_allow_child_type:
                row.prop(ui, 'child_as_gestures_item')
            else:
                row.label()

        if typ == 'menu_pie':
            DrawCustomUiFunc.draw_element_menu_pie(self, layout)

        for draw_prop in UI_LAYOUT_INCOMING_ITEMS[typ]:
            DrawCustomUiFunc.draw_element_prop(self, draw_prop, layout)

    def draw_element_menu_pie(self, layout: bpy.types.UILayout):
        layout.use_property_split = True
        layout.use_property_decorate = False
        ui = self.act_ui_element
        row = layout.row(align=True)
        row.prop(ui, 'is_use_box_style_pie')
        if not ui.is_use_box_style_pie:
            for draw_prop in UI_LAYOUT_INCOMING_ITEMS['column']:
                layout.prop(ui, draw_prop)

    def draw_element_prop(self, draw_prop, layout: bpy.types.UILayout):
        ui = self.act_ui_element
        prop = getattr(ui, draw_prop, None)
        DRAW = DrawCustomUiFunc
        layout.use_property_split = False
        layout.use_property_decorate = True

        def is_pr_sp(layout):
            layout.use_property_split = True
            layout.use_property_decorate = False

        if prop != None:
            if draw_prop == 'menu':
                DRAW.draw_element_menu(self, draw_prop, layout)
            elif draw_prop == 'icon':
                is_pr_sp(layout)
                DRAW.draw_element_icon(self, draw_prop, layout)
            elif draw_prop == 'property':
                is_pr_sp(layout)
                DRAW.draw_element_property(self, draw_prop, layout)
            elif draw_prop == 'operator':
                DRAW.draw_element_operator(self, draw_prop, layout)
            elif draw_prop == 'poll_string':
                DRAW.draw_element_poll(self, draw_prop, layout)
            elif draw_prop in ('text', 'heading'):
                is_pr_sp(layout)
                DRAW.draw_element_text(self, draw_prop, layout)
            else:
                is_pr_sp(layout)
                layout.prop(ui, draw_prop)

    def draw_element_text(self, draw_prop, layout: bpy.types.UILayout):
        ui = self.act_ui_element
        row = layout.row(align=True)
        row.prop(ui, draw_prop)
        row.prop(self.prefs, 'text_sync_update', text='', icon='FILE_REFRESH')

    def draw_element_menu(self, draw_prop, layout: bpy.types.UILayout):
        ui = self.act_ui_element
        row = layout.row(align=True)

        icon = 'FULLSCREEN_ENTER' if ui.menu_contents else 'FULLSCREEN_EXIT'
        row.prop(ui, draw_prop)
        row.prop(ui, 'menu_contents', icon=icon, text='')
        row.operator(UIElementItem.SelectMenu.bl_idname,
                     icon='MENU_PANEL')

    def draw_element_icon(self, draw_prop, layout: bpy.types.UILayout):
        ui = self.act_ui_element
        row = layout.row(align=True)
        # row.prop(ui, draw_prop)
        row.prop(ui, 'icon_only')
        row.operator(UIElementItem.SelectIcon.bl_idname,
                     icon='RESTRICT_SELECT_OFF')

    def draw_element_property(self, draw_prop, layout: bpy.types.UILayout):
        ui = self.act_ui_element
        row = layout.column(align=True)
        row.prop(ui, draw_prop)
        row.prop(ui, 'data')
        row.prop(ui, 'property_suffix')

    def draw_element_operator(self, draw_prop, layout: bpy.types.UILayout):
        ui = self.act_ui_element
        idname = UIElementItem.ApplyOperatorProperty.bl_idname

        def draw_head(layout, ui):
            row = layout.row(align=True)
            row.alert = not ui.is_available
            row.prop(ui, draw_prop)
            row.prop(ui, 'operator_context', text='')
            op = row.operator(idname,
                              icon='MENU_PANEL',
                              text='',
                              )
            op.is_popup_menu = True

        is_draw, lay = draw_extend_ui(layout,
                                      f'draw_element_operator_property',
                                      label='operator property',
                                      draw_func=draw_head,
                                      draw_func_data={'ui': ui},
                                      )

        if is_draw:
            row = lay.row(align=True)
            tmp_kmi_prop = ui.get_tmp_kmi_operator_property()
            able = row.alert = tmp_kmi_prop != ui.operator_property
            row.prop(ui, 'operator_property')

            op = row.operator(idname,
                              icon='FILE_REFRESH' if able else 'CHECKMARK',
                              text='操作符属性:'+ui.operator_property,
                              )
            op.is_popup_menu = False
            # 绘制临时kmi属性
            lay.template_keymap_item_properties(self.tmp_kmi)

    def draw_element_poll(self, draw_prop, layout: bpy.types.UILayout):
        DrawCustomUiFunc.draw_poll(self, self.act_ui_element, layout)

    def draw_element_advanced_parameter(self, layout: bpy.types.UILayout):
        '''
        绘制element高级属性

        '''
        layout.use_property_split = False
        layout.use_property_decorate = True
        ui = self.act_ui_element
        if Data.is_draw_type(ui.type) and ui.is_allow_child_type:
            def draw_head(layout, ui):
                layout.prop(ui, 'is_use_advanced_parameter')

            is_draw, lay = draw_extend_ui(layout,
                                          f'draw_element_advanced_parameter',
                                          label='order property',
                                          draw_func=draw_head,
                                          draw_func_data={'ui': ui},
                                          )
            uilayout = UI_LAYOUT_INCOMING_ITEMS['uilayout']

            if is_draw and ui and ui.is_allow_child_type:
                for prop in uilayout:
                    lay.prop(ui, prop)

    def draw_item_other_property(self, layout: bpy.types.UILayout):
        """
        绘制其它属性
        在UIlist列表上面
        """
        item = self.act_ui_item
        column = layout.column()

        if item.key.is_use_keymaps:
            DrawCustomUiFunc.draw_keymaps_set(self, column)
        typ = item.type
        if typ == 'panel':
            DrawCustomUiFunc.draw_panel(self, column)
        elif typ == 'menu_pie':
            DrawCustomUiFunc.draw_menu_pie(self, column)
        elif typ == 'menu':
            ...
        elif typ == 'layout':
            ...
    # poll

    def draw_poll(self, item, layout: bpy.types.UILayout):
        sp = layout.split(factor=0.15, align=True)

        sp.prop(item, 'type',
                text='',
                )

        row = sp.row(align=True)

        if item.type == 'else':
            row.label()
            row.label()
        else:
            row.prop(item, 'poll_string',
                     text='',
                     )

            row.operator(PollProperty.SetPollExpression.bl_idname,
                         text='',
                         icon='SETTINGS',
                         ).is_set_item_poll = (not item.is_ui_element)

    # panel

    def draw_panel_header(self, layout: bpy.types.UILayout):
        item = self.act_ui_item
        row = layout.row()
        row.label(text='面板属性')
        row.prop(item, 'bl_label')

    def draw_panel(self, layout: bpy.types.UILayout):

        is_draw, lay = draw_extend_ui(layout, 'draw_panel_extend',
                                      label='panel',
                                      default_extend=True,
                                      draw_func=DrawCustomUiFunc.draw_panel_header,
                                      draw_func_data={'self': self, },
                                      )

        if is_draw:
            item = self.act_ui_item
            box = lay.box()
            box.alignment = 'EXPAND'

            row = box.row()
            row.column().prop(item, 'space_type', text='空间类型', expand=True)

            col = row.column()
            col.prop(item, 'bl_category')
            col.prop(item, 'region_type', expand=True)
            col.prop(item, 'bl_options', expand=True)

    def draw_menu_pie(self, layout: bpy.types.UILayout):
        item = self.act_ui_item
        is_draw, lay = draw_extend_ui(
            layout, 'draw_menu_pie', label='饼菜单属性')

        if is_draw:
            col = lay.column(align=True)
            col.prop(item, 'use_gestures')
            for prop in pie_property_items:
                col.prop(item, prop)

    # key
    def draw_keymaps_set(self, layout: bpy.types.UILayout):
        """
        绘制快捷键的切换和显示
        """
        item = self.act_ui_item
        key = item.key
        uuid = item.uuid
        map_type = key.map_type

        is_draw, lay = draw_extend_ui(layout, 'draw_key_extend',
                                      label='key',
                                      default_extend=True,
                                      draw_func=DrawCustomUiFunc.draw_keymap_header,
                                      draw_func_data={'self': self, },
                                      )

        if is_draw:
            lay.active = key.is_enable_keymaps
            box = lay.box()

            if map_type not in {'TEXTINPUT', 'TIMER'}:
                DrawCustomUiFunc.draw_keymap(self, box)
            col = box.column()
            ro = col.row()
            ro.label(text=key.keymaps,)

            ro.operator(KeyMap.ShowKeymaps.bl_idname,
                        icon='STATUSBAR', text='')

            op = ro.operator(KeyMap.SetKeymaps.bl_idname,
                             icon='TOOL_SETTINGS', text='')
            op.uuid = uuid
            op.width = 600

    def draw_keymap_header(self, layout: bpy.types.UILayout):
        kmi = self.act_ui_item.key
        map_type = kmi.map_type

        split = layout.split(factor=0.5)

        row = split.row(align=False)
        row.prop(kmi, "is_enable_keymaps",
                 text=kmi.key_combination, emboss=True)

        row = split.row()
        row.active = kmi.is_enable_keymaps
        row.prop(kmi, "map_type", text="")

        if map_type == 'KEYBOARD':
            row.prop(kmi, "type", text="", event=True,
                     text_ctxt=ui_events_keymaps, icon='EVENT_OS')
        elif map_type == 'MOUSE':
            row.prop(kmi, "type", text="", event=True,
                     text_ctxt=ui_events_keymaps)
        elif map_type == 'NDOF':
            row.prop(kmi, "type", text=" ", event=True,
                     text_ctxt=ui_events_keymaps)
        elif map_type == 'TWEAK':
            sub_row = row.row()
            sub_row.prop(kmi, "type", text="", text_ctxt=ui_events_keymaps)
            sub_row.prop(kmi, "value", text="", text_ctxt=ui_events_keymaps)
        elif map_type == 'TIMER':
            row.prop(kmi, "type", text="", text_ctxt=ui_events_keymaps)
        else:
            row.label()
        ro = row.row()
        ro.prop(kmi, 'is_user_modifier', icon_only=True, icon='BACK')

    def draw_keymap(self, layout: bpy.types.UILayout):
        kmi = self.act_ui_item.key
        map_type = kmi.map_type

        sub = layout.column()
        sub_row = sub.row(align=True)
        if map_type == 'KEYBOARD':
            sub_row.prop(kmi, "type", text="", event=True,
                         text_ctxt=ui_events_keymaps)
            sub_row.prop(kmi, "value", text="",
                         text_ctxt=ui_events_keymaps)
            sub_row_repeat = sub_row.row(align=True)
            sub_row_repeat.active = kmi.value in {'ANY', 'PRESS'}

            sub_row_repeat.prop(kmi, "repeat", text="Repeat")
        elif map_type in {'MOUSE', 'NDOF'}:
            sub_row.prop(kmi, "type", text="",
                         text_ctxt=ui_events_keymaps)
            sub_row.prop(kmi, "value", text="",
                         text_ctxt=ui_events_keymaps)

        if map_type in {'KEYBOARD', 'MOUSE'} and kmi.value == 'CLICK_DRAG':
            sub_row = sub.row()
            sub_row.prop(kmi, "direction", text_ctxt=ui_events_keymaps)

        sub_row = sub.row()
        sub_row.scale_x = 0.75
        sub_row.prop(kmi, "any", text='Any', toggle=True)
        # Use `*_ui` properties as integers aren't practical.
        sub_row.prop(kmi, "shift", toggle=True)
        sub_row.prop(kmi, "ctrl", toggle=True)
        sub_row.prop(kmi, "alt", toggle=True)
        sub_row.prop(kmi, "oskey", text="Cmd", toggle=True)

        sub_row.prop(kmi, "key_modifier", text="", event=True,
                     text_ctxt=ui_events_keymaps)

        if kmi.value == 'DOUBLE_KEY':
            row = sub.row()
            row.prop(kmi, "double_key_time", toggle=True)
            row.prop(kmi, 'double_key', event=True)
        elif kmi.value == 'LONG_PRESS':
            row = sub.row()
            row.prop(kmi, "long_press_time", toggle=True)

    def draw_identical_keymaps(self, layout):
        '''
        from rna_keymap_ui import draw_keymaps
        key = self.act_ui_item.key
        if key.is_use_keymaps:
            com = key.key_combination

            is_draw, lay = draw_extend_ui(layout, 'draw_key_extend',
                                          label='key',
                                          default_extend=True,
                                          )
            if is_draw:
                draw_keymaps(bpy.context, layout.box())'''

    # test

    def draw_test(self, layout: bpy.types.UILayout):
        item = self.act_ui_item
        DrawCustomUiFunc._draw_key(self, layout, item)
        DrawCustomUiFunc._draw_ui_element(self, layout, item)
        DrawCustomUiFunc._draw_keymaps_item(self, layout, item)

    def _draw_key(self, layout, item):
        is_draw, lay = draw_extend_ui(layout, 'draw_keymaps_key', label='key')
        if is_draw:
            for pr in item.key.bl_rna.properties:
                if pr.identifier not in ('rna_type',):
                    lay.prop(item.key, pr.identifier)

    def _draw_ui_element(self, layout, item):
        is_draw, lay = draw_extend_ui(
            layout, 'draw_keymaps_ui_element', label='ui element')
        if is_draw and self.act_ui_element:
            for pr in self.act_ui_element.bl_rna.properties:
                if pr.identifier not in ('rna_type',):  # 'name',
                    lay.prop(self.act_ui_element, pr.identifier)

    def _draw_keymaps_item(self, layout, item):
        is_draw, lay = draw_extend_ui(
            layout, 'draw_keymaps_item', label='item')
        if is_draw:
            for pr in item.bl_rna.properties:
                if pr.identifier not in ('rna_type',):  # 'name',
                    lay.prop(item, pr.identifier)

