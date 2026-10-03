"""Insert the staged original Render method into its retail-free fixture."""
import argparse
from pathlib import Path


def generate(source, fixture):
    begin = source.index('void TrackedVehicleClass::Render(RenderInfoClass & rinfo)')
    end = source.index('\nvoid TrackedVehicleClass::Set_Model', begin)
    marker = '// ORIGINAL_RENDER_METHOD'
    if fixture.count(marker) != 1:
        raise ValueError('tracked-vehicle fixture must contain exactly one insertion marker')
    return fixture.replace(marker, source[begin:end])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generate(args.source.read_text(), args.fixture.read_text()))
