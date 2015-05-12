/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

extern crate layers;

use layers::platform::surface::NativeSurface;

#[derive(Copy, Clone)]
pub struct CanvasMetadata {
    pub surface_id: isize,
}

impl CanvasMetadata {
    pub fn from_native_surface(surface: &NativeSurface) -> CanvasMetadata {
        CanvasMetadata {
            surface_id: surface.get_id(),
        }
    }
}

