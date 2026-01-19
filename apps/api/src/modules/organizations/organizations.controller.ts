import { Controller, Get, Param, Query } from '@nestjs/common';

import { OrganizationsService } from './organizations.service.js';

@Controller('organizations')
export class OrganizationsController {
  constructor(private readonly organizationsService: OrganizationsService) {}

  @Get(':slug/roi')
  getOrgRoi(@Param('slug') slug: string) {
    return this.organizationsService.getOrganizationRoi(slug);
  }

  @Get(':slug/roi/timeseries')
  getOrgRoiTimeseries(@Param('slug') slug: string, @Query('days') days?: string) {
    const parsedDays = days ? Number.parseInt(days, 10) : undefined;
    return this.organizationsService.getOrganizationRoiTimeseries(slug, parsedDays);
  }
}
