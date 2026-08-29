/*
**	Command & Conquer Renegade(tm)
**	Copyright 2025 Electronic Arts Inc.
**
**	This program is free software: you can redistribute it and/or modify
**	it under the terms of the GNU General Public License as published by
**	the Free Software Foundation, either version 3 of the License, or
**	(at your option) any later version.
**
**	This program is distributed in the hope that it will be useful,
**	but WITHOUT ANY WARRANTY; without even the implied warranty of
**	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
**	GNU General Public License for more details.
**
**	You should have received a copy of the GNU General Public License
**	along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

/***********************************************************************************************
 ***              C O N F I D E N T I A L  ---  W E S T W O O D  S T U D I O S               ***
 ***********************************************************************************************
 *                                                                                             *
 *                 Project Name : Combat																		  *
 *                                                                                             *
 *                     $Archive:: /Commando/Code/wwui/menubackdrop.cpp         $*
 *                                                                                             *
 *                       Author:: Patrick Smith                                                *
 *                                                                                             *
 *                     $Modtime:: 11/21/01 11:30a                                             $*
 *                                                                                             *
 *                    $Revision:: 8                                                           $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#include "menubackdrop.h"
#include "scene.h"
#include "camera.h"
#include "ww3d.h"
#include "assetmgr.h"
#include "render2d.h"
#include "light.h"
#include "hanim.h"

#if defined(__vita__) && defined(RENEGADE_A4_ORIGINAL_FRONTEND)
#include "vita/a30_vita_runtime.h"
#define A4_BACKDROP_TRACE(...) A30_Vita_Log(__VA_ARGS__)
#else
#define A4_BACKDROP_TRACE(...) ((void)0)
#endif


////////////////////////////////////////////////////////////////
//
//	MenuBackDropClass
//
////////////////////////////////////////////////////////////////
MenuBackDropClass::MenuBackDropClass (void)	:
	Scene (NULL),
	Camera (NULL),
	Model (NULL),
	Anim (NULL),
	ClearScreen (true)
{	
	//
	//	Create a scene to use for the background
	//
	Scene = new SimpleSceneClass;
	if (Scene != NULL) {
		Scene->Set_Ambient_Light (Vector3(1, 1, 1));
	} else {
		A4_BACKDROP_TRACE("A4 menu backdrop: SimpleScene allocation failed this=%p\n", this);
	}

	//
	// Create a single scene light
	//
	LightClass *light = new LightClass;
	if (light != NULL && Scene != NULL) {

		//
		// Configure the light
		//
		light->Set_Position (Vector3 (0, 0, 15000.0F));
		light->Set_Intensity (1.0F);
		light->Set_Force_Visible(true);
		light->Set_Flag (LightClass::NEAR_ATTENUATION, false);
		light->Set_Far_Attenuation_Range (1000000, 1000000);
		light->Set_Ambient(Vector3 (0,0,0));
		light->Set_Diffuse (Vector3 (1.0F, 1.0F, 1.0F));
		light->Set_Specular (Vector3 (1.0F, 1.0F, 1.0F));

		//
		// Add this light to the scene
		//
		Scene->Add_Render_Object (light);
		REF_PTR_RELEASE(light);
	} else if (light != NULL) {
		REF_PTR_RELEASE(light);
	}

	//
	//	Create a camera to use in background-scene
	//	
	Camera = new CameraClass();
	if (Camera != NULL) {
		Camera->Set_Position (Vector3 (0, 0, 800));
	} else {
		A4_BACKDROP_TRACE("A4 menu backdrop: Camera allocation failed this=%p scene=%p\n",
			this, Scene);
	}

	//
	//	Configure the view plane
	//
	if (Camera != NULL) {
		const RectClass &screen_size = Render2DClass::Get_Screen_Resolution ();
		float hfov = DEG_TO_RAD(45.0F);
		float vfov = (screen_size.Height () / screen_size.Width ()) * hfov;
		Camera->Set_View_Plane (hfov, vfov);

		//
		//	Set the clip planes
		//
		Camera->Set_Clip_Planes (5.0F, 12000.0F);
	}
	A4_BACKDROP_TRACE("A4 menu backdrop: constructed this=%p scene=%p camera=%p\n",
		this, Scene, Camera);
	return ;
}


////////////////////////////////////////////////////////////////
//
//	~MenuBackDropClass
//
////////////////////////////////////////////////////////////////
MenuBackDropClass::~MenuBackDropClass (void)
{
	Remove_Model();
	REF_PTR_RELEASE (Camera);
	REF_PTR_RELEASE (Scene);
	return ;
}


////////////////////////////////////////////////////////////////
//
//	Render
//
////////////////////////////////////////////////////////////////
void
MenuBackDropClass::Render (void)
{
	if (Scene == NULL || Camera == NULL) {
		static bool logged_missing_render_state = false;
		if (!logged_missing_render_state) {
			A4_BACKDROP_TRACE("A4 menu backdrop: render skipped scene=%p camera=%p\n",
				Scene, Camera);
			logged_missing_render_state = true;
		}
		return ;
	}
	//
	//	Simple render the scene
	//
	WW3D::Render (Scene, Camera, ClearScreen, ClearScreen);
	return ;
}


////////////////////////////////////////////////////////////////
//
//	Set_Model
//
////////////////////////////////////////////////////////////////
void
MenuBackDropClass::Set_Model (const char *name)
{
	//	Get rid of the old model.
	Remove_Model();

	//
	//	Load the new model
	//
	Model = WW3DAssetManager::Get_Instance ()->Create_Render_Obj (name);
	A4_BACKDROP_TRACE("A4 menu backdrop: Set_Model name=%s model=%p scene=%p camera=%p\n",
		name != NULL ? name : "(null)", Model, Scene, Camera);
	if (Model != NULL) {

		//
		//	Check to see if this model has a camera bone
		//
		int camera_bone_index = Model->Get_Bone_Index ("CAMERA");
		if (camera_bone_index > 0 && Camera != NULL) {
			
			//
			// Convert the bone's transform into a camera transform
			//
			const Matrix3D &tm = Model->Get_Bone_Transform (camera_bone_index);
			Matrix3D cam_tm (Vector3 (0, -1, 0), Vector3 (0, 0, 1), Vector3 (-1, 0, 0), Vector3 (0, 0, 0));
			Matrix3D new_tm = tm * cam_tm;

			//
			//	Set the camera's new transform
			//
			Camera->Set_Transform (new_tm);
		}

		//
		//	Add the model to the scene
		//
		if (Scene != NULL) {
			Scene->Add_Render_Object (Model);
		} else {
			A4_BACKDROP_TRACE("A4 menu backdrop: scene unavailable for model=%p\n",
				Model);
		}
	}

	//
	//	Update the animation
	//
	Play_Animation ();
	return ;
}


////////////////////////////////////////////////////////////////
//
//	Remove_Model
//
////////////////////////////////////////////////////////////////
void
MenuBackDropClass::Remove_Model (void)
{
	if (Model != NULL) {
		Model->Remove();
	}
	REF_PTR_RELEASE (Model);
	REF_PTR_RELEASE (Anim);
}


////////////////////////////////////////////////////////////////
//
//	Set_Animation
//
////////////////////////////////////////////////////////////////
void
MenuBackDropClass::Set_Animation (const char *anim_name)
{
	REF_PTR_RELEASE (Anim);
	AnimationName = anim_name;
	Play_Animation ();
	return ;
}


////////////////////////////////////////////////////////////////
//
//	Set_Animation_Percentage
//
////////////////////////////////////////////////////////////////
void
MenuBackDropClass::Set_Animation_Percentage (float percent)
{
	if ( Model != NULL && Anim != NULL ) {
		float frame = (float)(Anim->Get_Num_Frames()-1) * WWMath::Clamp( percent, 0, 1 );
		Model->Set_Animation (Anim, frame, RenderObjClass::ANIM_MODE_MANUAL);
	}
	return ;
}


////////////////////////////////////////////////////////////////
//
//	Play_Animation
//
////////////////////////////////////////////////////////////////
void
MenuBackDropClass::Play_Animation (void)
{
	if (Model == NULL) {
		return ;
	}
	
	if (AnimationName.Get_Length () > 0) {
		
		//
		//	Play the animation on the background (if necessary)
		//
		REF_PTR_RELEASE (Anim);
		Anim = WW3DAssetManager::Get_Instance ()->Get_HAnim (AnimationName);
		if (Anim != NULL) {
			Model->Set_Animation (Anim, 0, RenderObjClass::ANIM_MODE_LOOP);
		}

	} else {

		//
		//	Stop the animation
		//
		REF_PTR_RELEASE (Anim);
		Model->Set_Animation (NULL);
	}
	
	return ;
}
