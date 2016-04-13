import matplotlib
matplotlib.use('Agg')

from argparse import ArgumentParser
from crosscompute_table import TableType
from invisibleroads_macros.disk import make_enumerated_folder_for, make_folder
from invisibleroads_macros.log import format_summary
from matplotlib import pyplot as plt
from os.path import join


def run(
					target_folder,
					point_table,
					point_table_x_column,
					point_table_y_column):
	xys = point_table[[point_table_x_column, point_table_y_column]].values
	figure = plt.figure()
	plt.scatter(xys[:, 0], xys[:, 1])
	image_path = join(target_folder, 'points.png')
	figure.savefig(image_path)
	return [	
		('points_image_path', image_path),
	]


if __name__ == '__main__':
	argument_parser = ArgumentParser()
	argument_parser.add_argument(
		'--target_folder',
		metavar='FOLDER', type=make_folder)
	argument_parser.add_argument(
		'--point_table_path',
		metavar='PATH', required=True)
	argument_parser.add_argument(
		'--point_table_x_column',
		metavar='COLUMN', required=True)
	argument_parser.add_argument(
		'--point_table_y_column',
		metavar='COLUMN', required=True)
	
	args = argument_parser.parse_args()
	d = run(
		args.target_folder or make_enumerated_folder_for(__file__),
		TableType.load(args.point_table_path),
		args.point_table_x_column,
		args.point_table_y_column)
	print(format_summary(d))
	 