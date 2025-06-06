from pygame import Surface


class Camera:
    def __init__(self, screen, camera_size):
        self.image = Surface.subsurface(screen, (0, 0, camera_size[0], camera_size[1]))  # Camera image
        camera_w, camera_h = self.image.get_rect().size  # get size of camera
        self.camera_w_center = camera_w / 2
        self.camera_h_center = camera_h / 2

    def update(self, pos, surfaces):
        """Update self camera with sprite blit to camera image"""
        camera_x = pos[0] - self.camera_w_center  # Current camera center x
        camera_y = pos[1] - self.camera_h_center  # Current camera center y
        for surface in surfaces:  # Blit sprite to camara image
            surface_x, surface_y = surface.rect.left, surface.rect.top
            surface_w, surface_h = surface.rect.size
            if surface_x + surface_w - camera_x > 0 and surface_y + surface_h - camera_y > 0:
                # only blit if image in camera at all
                self.image.blit(surface.image, (surface_x - camera_x, surface_y - camera_y))

    def out_update(self, out_surfaces):
        for surface in out_surfaces:  # surface that get blit with pos on screen instead of in battle
            self.image.blit(surface.image, surface.rect)
