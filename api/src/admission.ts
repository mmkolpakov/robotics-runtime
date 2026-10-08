import {ApiError} from './database.js';
export const uuid={type:'string',pattern:'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'};
export const text={type:'string',minLength:1,maxLength:256};
export function projectIdentifier(value:string){if(!new RegExp(uuid.pattern).test(value))throw new ApiError(400,'invalid project identifier');return value}
export function branchName(value:string|null|undefined){if(typeof value!=='string'||value.length<text.minLength||value.length>text.maxLength)throw new ApiError(400,'existing branch name required');return value}
