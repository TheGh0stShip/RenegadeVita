// Original EA dx8wrapper.cpp frame-counter lifecycle, retained at the platform boundary.
// Definitions below are copied verbatim; CPU boundary calls remain distinct from GPU work.
static unsigned				last_frame_matrix_changes								= 0;
static unsigned				last_frame_material_changes							= 0;
static unsigned				last_frame_vertex_buffer_changes						= 0;
static unsigned				last_frame_index_buffer_changes						= 0;
static unsigned				last_frame_light_changes								= 0;
static unsigned				last_frame_texture_changes								= 0;
static unsigned				last_frame_render_state_changes						= 0;
static unsigned				last_frame_texture_stage_state_changes				= 0;
static unsigned				last_frame_number_of_DX8_calls						= 0;

unsigned DX8Wrapper::material_changes = 0;
unsigned DX8Wrapper::vertex_buffer_changes = 0;
unsigned DX8Wrapper::index_buffer_changes = 0;
unsigned DX8Wrapper::light_changes = 0;

void DX8Wrapper::Reset_Statistics()
{
	matrix_changes	= 0;
	material_changes = 0;
	vertex_buffer_changes = 0;
	index_buffer_changes = 0;
	light_changes = 0;
	texture_changes = 0;
	render_state_changes =0;
	texture_stage_state_changes =0;

	number_of_DX8_calls = 0;
	last_frame_matrix_changes = 0;
	last_frame_material_changes = 0;
	last_frame_vertex_buffer_changes = 0;
	last_frame_index_buffer_changes = 0;
	last_frame_light_changes = 0;
	last_frame_texture_changes = 0;
	last_frame_render_state_changes = 0;
	last_frame_texture_stage_state_changes = 0;
	last_frame_number_of_DX8_calls = 0;
}

void DX8Wrapper::Begin_Statistics()
{
	matrix_changes=0;
	material_changes=0;
	vertex_buffer_changes=0;
	index_buffer_changes=0;
	light_changes=0;
	texture_changes = 0;
	render_state_changes =0;
	texture_stage_state_changes =0;
	number_of_DX8_calls=0;
}

void DX8Wrapper::End_Statistics()
{
	last_frame_matrix_changes=matrix_changes;
	last_frame_material_changes=material_changes;
	last_frame_vertex_buffer_changes=vertex_buffer_changes;
	last_frame_index_buffer_changes=index_buffer_changes;
	last_frame_light_changes=light_changes;
	last_frame_texture_changes = texture_changes;
	last_frame_render_state_changes = render_state_changes;
	last_frame_texture_stage_state_changes = texture_stage_state_changes;
	last_frame_number_of_DX8_calls=number_of_DX8_calls;
}

unsigned DX8Wrapper::Get_Last_Frame_Matrix_Changes()			{ return last_frame_matrix_changes; }
unsigned DX8Wrapper::Get_Last_Frame_Material_Changes()		{ return last_frame_material_changes; }
unsigned DX8Wrapper::Get_Last_Frame_Vertex_Buffer_Changes()	{ return last_frame_vertex_buffer_changes; }
unsigned DX8Wrapper::Get_Last_Frame_Index_Buffer_Changes()	{ return last_frame_index_buffer_changes; }
unsigned DX8Wrapper::Get_Last_Frame_Light_Changes()			{ return last_frame_light_changes; }
unsigned DX8Wrapper::Get_Last_Frame_Texture_Changes()			{ return last_frame_texture_changes; }
unsigned DX8Wrapper::Get_Last_Frame_Render_State_Changes()	{ return last_frame_render_state_changes; }
unsigned DX8Wrapper::Get_Last_Frame_Texture_Stage_State_Changes()	{ return last_frame_texture_stage_state_changes; }
unsigned DX8Wrapper::Get_Last_Frame_DX8_Calls()					{ return last_frame_number_of_DX8_calls; }
